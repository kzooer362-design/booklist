#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
腾讯云 SCF 版 - 读书会图书搜索服务
适配 Serverless 运行时，Flask 应用通过 wsgi 适配
"""

import os
import sys
import json
import hashlib
import re
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, request, jsonify, Response

app = Flask(__name__)

REQUEST_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}

try:
    import requests
    from bs4 import BeautifulSoup
    HAS_EXTERNAL_DEPS = True
except ImportError:
    HAS_EXTERNAL_DEPS = False


def _normalize_title(title):
    if not title:
        return ''
    t = title.lower().strip()
    t = re.sub(r'[（(【\[].*?[)）】\]]', '', t)
    t = re.sub(r'[:：—\-_].*$', '', t)
    return t.strip()


def _normalize_author(author):
    if not author:
        return ''
    a = author.strip()
    simp_trad = {'韓': '韩', '江': '江', '東': '东', '關': '关', '係': '系', '裏': '里', '為': '为'}
    for k, v in simp_trad.items():
        a = a.replace(k, v)
    return a


def _book_score(book):
    score = 0
    if book.get('author'):
        score += 2
    if book.get('cover'):
        score += 2
    if book.get('description') and len(book['description']) > 50:
        score += 2
    if book.get('publishedYear'):
        score += 1
    score += book.get('source_count', 1)
    return score


def filter_best_match(books, query=''):
    if not books:
        return []
    groups = {}
    for book in books:
        title_key = _normalize_title(book.get('title', ''))
        if not title_key:
            continue
        if title_key not in groups or _book_score(book) > _book_score(groups[title_key]):
            groups[title_key] = book
    filtered = list(groups.values())
    query_norm = _normalize_title(query)
    def match_score(b):
        title_norm = _normalize_title(b.get('title', ''))
        exact = 10 if title_norm == query_norm else 0
        return exact + _book_score(b)
    filtered.sort(key=match_score, reverse=True)
    if query_norm:
        exact_matches = [b for b in filtered if _normalize_title(b.get('title', '')) == query_norm]
        if exact_matches:
            return exact_matches[:3]
    return filtered[:3] if len(filtered) > 1 else filtered[:1]


def search_douban_suggest(query):
    if not HAS_EXTERNAL_DEPS:
        return []
    url = 'https://book.douban.com/j/subject_suggest'
    try:
        resp = requests.get(url, params={'q': query}, headers=REQUEST_HEADERS, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            books = []
            for item in data:
                if item.get('type') == 'book':
                    books.append({
                        'title': item.get('title', ''),
                        'author': item.get('author', ''),
                        'cover': item.get('img'),
                        'description': '',
                        'publishedYear': item.get('year', ''),
                        'detail_url': item.get('url', ''),
                        'source_count': 1,
                        'sources': ['douban_suggest'],
                    })
            return books
    except Exception:
        pass
    return []


def search_openlibrary(query):
    if not HAS_EXTERNAL_DEPS:
        return []
    url = 'https://openlibrary.org/search.json'
    try:
        resp = requests.get(url, params={'q': query, 'limit': 10}, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            books = []
            for doc in data.get('docs', []):
                books.append({
                    'title': doc.get('title', ''),
                    'author': doc.get('author_name', ['未知'])[0] if doc.get('author_name') else '未知',
                    'cover': f"https://covers.openlibrary.org/b/id/{doc['cover_i']}-L.jpg" if doc.get('cover_i') else '',
                    'description': doc.get('first_sentence', [''])[0] if doc.get('first_sentence') else '',
                    'publishedYear': str(doc.get('first_publish_year', '')),
                    'source_count': 1,
                    'sources': ['openlibrary'],
                })
            return books
    except Exception:
        pass
    return []


def search_bing_image(query):
    if not HAS_EXTERNAL_DEPS:
        return []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept-Language': 'zh-CN,zh;q=0.9',
    }
    url = 'https://www.bing.com/images/search'
    try:
        resp = requests.get(url, params={'q': f'{query} 书籍 封面', 'form': 'HDRSC2'}, headers=headers, timeout=8)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            covers = []
            for img in soup.select('img.mimg'):
                src = img.get('src', '')
                if src and 'http' in src and len(covers) < 3:
                    covers.append(src)
            return covers
    except Exception:
        pass
    return []


def search_baidu_image(query):
    if not HAS_EXTERNAL_DEPS:
        return []
    url = 'https://image.baidu.com/search/acjson'
    try:
        resp = requests.get(url, params={
            'tn': 'resultjson_com',
            'word': f'{query} 书籍 封面',
            'pn': 0,
            'rn': 3,
        }, headers=REQUEST_HEADERS, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            covers = []
            for item in data.get('data', []):
                if item.get('thumbURL') and len(covers) < 3:
                    covers.append(item['thumbURL'])
            return covers
    except Exception:
        pass
    return []


def fill_missing_covers(books):
    missing = [(i, b) for i, b in enumerate(books) if not b.get('cover')]
    if not missing:
        return

    def fill_one(idx_book):
        idx, book = idx_book
        title = book.get('title', '')
        if not title:
            return idx, None
        covers = search_bing_image(title)
        if not covers:
            covers = search_baidu_image(title)
        if covers:
            return idx, covers[0]
        return idx, None

    with ThreadPoolExecutor(max_workers=min(4, len(missing))) as executor:
        futures = {executor.submit(fill_one, item): item for item in missing}
        for future in futures:
            idx, cover = future.result()
            if cover and idx < len(books):
                books[idx]['cover'] = cover


def merge_and_score(results):
    merged = {}
    for source_books in results:
        for book in source_books:
            key = _normalize_title(book.get('title', ''))
            if not key:
                continue
            if key in merged:
                existing = merged[key]
                for field in ['author', 'cover', 'description', 'publishedYear']:
                    if not existing.get(field) and book.get(field):
                        existing[field] = book[field]
                existing['source_count'] = existing.get('source_count', 1) + 1
                existing['sources'].extend(book.get('sources', []))
            else:
                merged[key] = dict(book)
    return list(merged.values())


@app.route('/api/search', methods=['GET'])
def search():
    query = request.args.get('q', '').strip()
    sources_param = request.args.get('sources', 'douban_suggest,openlibrary')

    if not query:
        return jsonify({'success': False, 'error': '请输入书名'}), 400

    sources = [s.strip() for s in sources_param.split(',')]

    search_funcs = {
        'douban_suggest': search_douban_suggest,
        'openlibrary': search_openlibrary,
    }

    all_books = []
    with ThreadPoolExecutor(max_workers=len(sources)) as executor:
        futures = {}
        for src in sources:
            if src in search_funcs:
                futures[executor.submit(search_funcs[src], query)] = src
        for future in futures:
            try:
                result = future.result(timeout=15)
                all_books.append(result)
            except Exception:
                all_books.append([])

    merged = merge_and_score(all_books)
    fill_missing_covers(merged)
    final = filter_best_match(merged, query)

    return jsonify({
        'success': True,
        'books': final,
        'total': len(final),
        'from_cache': False,
        'sources_used': sources,
    })


@app.route('/api/cover', methods=['GET'])
def proxy_cover():
    target_url = request.args.get('url', '')
    if not target_url or not target_url.startswith('http'):
        return jsonify({'error': 'invalid url'}), 400

    try:
        from urllib.parse import urlparse
        parsed = urlparse(target_url)
        referer = f'{parsed.scheme}://{parsed.netloc}/'
        if HAS_EXTERNAL_DEPS:
            resp = requests.get(target_url, headers={
                'User-Agent': REQUEST_HEADERS['User-Agent'],
                'Referer': referer,
            }, timeout=8)
            if resp.status_code == 200:
                content_type = resp.headers.get('Content-Type', 'image/jpeg')
                if 'image' not in content_type:
                    content_type = 'image/jpeg'
                return Response(resp.content, content_type=content_type)
            else:
                return jsonify({'error': f'upstream {resp.status_code}'}), resp.status_code
        else:
            return jsonify({'error': 'external deps not available'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'ok',
        'mode': 'tencent-scf',
        'text_sources': ['douban_suggest', 'openlibrary'],
        'image_sources': ['baidu_image', 'bing_image'],
        'strategy': 'divide_and_conquer',
        'external_deps': HAS_EXTERNAL_DEPS,
    })


def handler(event, context):
    """腾讯云 SCF 入口函数"""
    from werkzeug.wrappers import Request as ScfRequest
    from werkzeug.serving import WSGIRequestHandler

    # 将 SCF event 转换为 WSGI 环境
    environ = {
        'wsgi.version': (1, 0),
        'wsgi.input': __import__('io').BytesIO(event.get('body', '').encode('utf-8') if isinstance(event.get('body'), str) else event.get('body', b'')),
        'wsgi.errors': __import__('sys').stderr,
        'wsgi.multiprocess': False,
        'wsgi.multithread': False,
        'wsgi.run_once': False,
        'REQUEST_METHOD': event.get('httpMethod', 'GET'),
        'PATH_INFO': event.get('path', '/'),
        'QUERY_STRING': event.get('queryString', ''),
        'SERVER_NAME': 'localhost',
        'SERVER_PORT': '80',
        'SERVER_PROTOCOL': 'HTTP/1.1',
        'HTTP_HOST': event.get('headers', {}).get('Host', 'localhost'),
        'CONTENT_TYPE': event.get('headers', {}).get('Content-Type', ''),
        'CONTENT_LENGTH': str(len(event.get('body', ''))),
    }

    for key, value in event.get('headers', {}).items():
        wsgi_key = 'HTTP_' + key.upper().replace('-', '_')
        environ[wsgi_key] = value

    # 处理路由
    url_path = event.get('path', '/')
    query_string = event.get('queryString', '')
    method = event.get('httpMethod', 'GET')

    # 简化处理：直接用 Flask test client
    with app.test_client() as client:
        if method == 'GET':
            resp = client.get(f'{url_path}?{query_string}')
        elif method == 'POST':
            resp = client.post(f'{url_path}?{query_string}')
        else:
            return {'statusCode': 405, 'body': 'Method Not Allowed'}

        resp_body = resp.get_data(as_text=True)
        resp_headers = dict(resp.headers)

        return {
            'statusCode': resp.status_code,
            'headers': resp_headers,
            'body': resp_body,
            'isBase64Encoded': False,
        }


# 本地开发用
if __name__ == '__main__':
    port = int(os.environ.get('PORT', '5000'))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
