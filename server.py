#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
读书会图书搜索服务 - 分治聚合版

核心思路：分而治之（Divide & Conquer）
- 文字源（title/author/description）: 豆瓣/微信读书/京东/当当/OpenLibrary/Google/mq59/Amazon/百度百科
- 图片源（cover）: 百度图片/Bing图片（为缺封面书兜底）
- 各字段击中一个源即可使用，不必强求一个源给全所有信息
- 单次请求返回尽可能多的高质量结果
"""

import os
import json
import time
import hashlib
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup

# 静态文件目录指向当前目录（托管 index.html/app.js/style.css）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=BASE_DIR, static_url_path='')
CORS(app)


@app.route('/')
def index():
    """返回前端首页"""
    return app.send_static_file('index.html')

CACHE_DIR = os.path.join(os.path.dirname(__file__), 'cache')
os.makedirs(CACHE_DIR, exist_ok=True)

REQUEST_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}


def get_cache_path(query):
    key = hashlib.md5(query.encode('utf-8')).hexdigest()
    return os.path.join(CACHE_DIR, f'{key}.json')


def load_cache(query):
    path = get_cache_path(query)
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if time.time() - data.get('timestamp', 0) < 86400:
                return data.get('books', [])
        except Exception:
            pass
    return None


def save_cache(query, books):
    path = get_cache_path(query)
    data = {
        'query': query,
        'timestamp': time.time(),
        'books': books
    }
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f'保存缓存失败: {e}')


def clean_text(text):
    if not text:
        return ''
    return re.sub(r'\s+', ' ', text).strip()


def extract_first_n(text, max_len=300):
    text = clean_text(text)
    if len(text) > max_len:
        return text[:max_len] + '...'
    return text


def search_douban_simple(query):
    """豆瓣搜索 - 解析HTML页面结果"""
    print(f'[豆瓣] 搜索: {query}')
    books = []

    search_url = f'https://search.douban.com/book/subject_search?search_text={requests.utils.quote(query)}&cat=1001'

    try:
        resp = requests.get(search_url, headers=REQUEST_HEADERS, timeout=5)
        resp.encoding = 'utf-8'
        if resp.status_code != 200:
            return []

        soup = BeautifulSoup(resp.text, 'lxml')

        items = soup.select('.item-root')
        if not items:
            items = soup.select('.subject-item')
        if not items:
            items = []
            for link in soup.select('a[href*="book.douban.com/subject"]'):
                parent = link.parent
                while parent and parent.name not in ('div', 'li', 'article'):
                    parent = parent.parent
                if parent:
                    items.append(parent)

        for item in items[:15]:
            try:
                book = {}

                title_el = item.select_one('.title-text') or item.select_one('a.title') or item.select_one('.subject-title')
                if not title_el:
                    for a in item.select('a'):
                        href = a.get('href', '')
                        if 'book.douban.com' in href or '/subject/' in href:
                            title_el = a
                            break
                if title_el:
                    book['title'] = clean_text(title_el.get_text())
                    href = title_el.get('href', '')
                    if href and href.startswith('http'):
                        book['detail_url'] = href
                    elif href and href.startswith('/'):
                        book['detail_url'] = 'https://search.douban.com' + href

                cover_el = item.select_one('img')
                if cover_el:
                    book['cover'] = cover_el.get('data-original') or cover_el.get('src') or ''
                    if book['cover'] and book['cover'].startswith('//'):
                        book['cover'] = 'https:' + book['cover']

                abstract_el = item.select_one('.abstract') or item.select_one('.pub')
                if abstract_el:
                    text = clean_text(abstract_el.get_text())
                    author_match = re.search(r'作者[:：]\s*([^/\n]+)', text)
                    if author_match:
                        book['author'] = clean_text(author_match.group(1))
                    else:
                        parts = text.split('/')
                        if parts:
                            candidate = parts[0].strip()
                            if candidate and not re.match(r'^\d{4}$', candidate):
                                book['author'] = candidate

                if book.get('title') and len(book['title']) > 1:
                    books.append(book)
            except Exception:
                continue

        seen = set()
        unique = []
        for b in books:
            key = b.get('title', '').lower()
            if key and key not in seen:
                seen.add(key)
                unique.append(b)

        print(f'[豆瓣] 找到 {len(unique)} 本书')
        return unique[:15]

    except Exception as e:
        print(f'[豆瓣] 搜索异常: {e}')
        return []



def parse_douban_subject(sid, headers=None):
    """公共函数：解析豆瓣书籍详情页，返回 title/author/cover/description/publishedYear/detail_url"""
    url = f'https://book.douban.com/subject/{sid}/'
    default_headers = {
        **REQUEST_HEADERS,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Referer': 'https://book.douban.com/',
    }
    use_headers = headers or default_headers
    try:
        r = requests.get(url, headers=use_headers, timeout=5)
        if r.status_code != 200:
            return None
        soup = BeautifulSoup(r.text, 'html.parser')
        # 标题
        title_el = soup.select_one('#wrapper h1 span') or soup.select_one('#wrapper h1') or soup.select_one('h1')
        title = clean_text(title_el.get_text()) if title_el else ''
        # 去掉书名号
        if title.startswith('《') and title.endswith('》'):
            title = title[1:-1]
        if not title:
            return None
        # 作者 - 用原始 get_text 保留换行，避免 clean_text 压缩换行导致正则匹配整行
        author = ''
        info_block = soup.select_one('#info')
        if info_block:
            raw_info_text = info_block.get_text()  # 保留原始换行
            # 优先用精确正则：作者: xxx (遇到译者/出版社/出品方等停止词截断)
            m = re.search(r'作者[:：]\s*([^\n译者出版社出品方原作名丛书ISBN页数装帧定价]+)', raw_info_text)
            if m:
                author = clean_text(m.group(1))
            else:
                # 兜底：取 #info 下第一个 <a> 标签（豆瓣作者通常是第一个链接）
                a_tag = info_block.select_one('a')
                if a_tag:
                    candidate = clean_text(a_tag.get_text())
                    if candidate and len(candidate) < 50 and not re.match(r'^\d+$', candidate):
                        author = candidate
        if not author:
            a_tag = soup.select_one('#info a') or soup.select_one('a[href*="/author/"]')
            if a_tag:
                author = clean_text(a_tag.get_text())
        # 封面
        cover = ''
        img_el = soup.select_one('#mainpic img') or soup.select_one('#wrapper .nbg img') or soup.select_one('a.nbg img')
        if img_el:
            cover = img_el.get('src', '') or img_el.get('data-origin', '') or ''
        if cover and cover.startswith('//'):
            cover = 'https:' + cover
        # 出版年份
        published_year = ''
        if info_block:
            m = re.search(r'(\d{4})\s*年?\s*(\d+)?\s*月?\s*-\s*\d+\s*元', info_block.get_text())
            if m:
                published_year = m.group(1)
            else:
                m2 = re.search(r'(\d{4})\s*-\s*\d+', info_block.get_text())
                if m2:
                    published_year = m2.group(1)
                else:
                    m3 = re.search(r'出版年[:：]\s*(\d{4})', info_block.get_text())
                    if m3:
                        published_year = m3.group(1)
        # 简介
        desc = ''
        intro_els = soup.select('#link-report .intro') or soup.select('.related_info .intro') or soup.select('.intro')
        for intro in intro_els:
            text = clean_text(intro.get_text())
            if text and len(text) > 20 and _is_chinese_text(text, 0.4):
                desc = extract_first_n(text, 300)
                break
        return {
            'title': title,
            'author': author,
            'cover': cover,
            'description': desc,
            'detail_url': url,
            'publishedYear': published_year,
            '_source': 'douban_search_page',
            '_douban_id': sid,
        }
    except Exception as e:
        print(f'  [详情页] subject/{sid} 解析失败: {e}')
        return None


def search_douban_search_page(query):
    """
    豆瓣搜索主流程（用户指定的链路）：
    1. 请求豆瓣读书搜索页 HTML → 解析提取 subject_id
    2. 并发抓取每个 subject 的详情页拿完整信息
    """
    print(f'[豆瓣搜索页] 查询: {query}')
    books = []
    search_url = f'https://search.douban.com/book/subject_search?search_text={requests.utils.quote(query)}&cat=1001'
    headers = {
        **REQUEST_HEADERS,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Referer': 'https://book.douban.com/',
    }
    try:
        resp = requests.get(search_url, headers=headers, timeout=8)
        resp.encoding = 'utf-8'
        if resp.status_code != 200:
            print(f'[豆瓣搜索页] HTTP {resp.status_code}')
            return []
        html = resp.text
        # ===== 方式1：正则直接提取所有 subject id =====
        subject_ids = re.findall(r'book\.douban\.com/subject/(\d+)', html)
        # ===== 方式2：BeautifulSoup 兜底 =====
        if not subject_ids:
            soup = BeautifulSoup(html, 'html.parser')
            for a in soup.select('a[href*="subject/"]'):
                href = a.get('href', '')
                m = re.search(r'subject/(\d+)', href)
                if m:
                    subject_ids.append(m.group(1))
            # 再兜底：扫整个页面链接
            if not subject_ids:
                for a in soup.find_all('a', href=True):
                    m = re.search(r'subject/(\d+)', a['href'])
                    if m:
                        subject_ids.append(m.group(1))
        # 去重保序，取前20个
        seen = set()
        unique_ids = []
        for sid in subject_ids:
            if sid not in seen:
                seen.add(sid)
                unique_ids.append(sid)
        unique_ids = unique_ids[:20]
        if not unique_ids:
            print(f'[豆瓣搜索页] 未提取到 subject_id')
            return []
        print(f'[豆瓣搜索页] 提取到 {len(unique_ids)} 个 subject_id, 并发抓详情页')
        # ===== 并发抓详情页（并发限制3，避免豆瓣限流） =====
        filled = 0
        with ThreadPoolExecutor(max_workers=min(3, len(unique_ids))) as executor:
            for result in executor.map(lambda sid: parse_douban_subject(sid, headers), unique_ids):
                if result and result.get('title'):
                    sid = result.get('_douban_id', '')
                    if sid not in seen or True:  # unique_ids 已去重
                        books.append(result)
                        filled += 1
        print(f'[豆瓣搜索页] 成功解析 {filled}/{len(unique_ids)} 本')
        return books
    except Exception as e:
        print(f'[豆瓣搜索页] 异常: {e}')
        return []


def search_weread(query):
    """微信读书搜索"""
    print(f'[微信读书] 搜索: {query}')

    search_url = f'https://weread.qq.com/web/search/book?keyword={requests.utils.quote(query)}'

    try:
        resp = requests.get(search_url, headers=REQUEST_HEADERS, timeout=6)
        resp.encoding = 'utf-8'
        if resp.status_code != 200:
            return []

        data = resp.json()
        books = []

        for item in data.get('data', {}).get('books', [])[:15]:
            book = {}
            book['title'] = item.get('book', {}).get('title', '')
            book['author'] = ', '.join(item.get('book', {}).get('author', [])) if isinstance(item.get('book', {}).get('author'), list) else item.get('book', {}).get('author', '')
            book['cover'] = item.get('book', {}).get('cover', '')
            book['description'] = item.get('book', {}).get('intro', '') or item.get('book', {}).get('introduction', '')

            if book.get('title'):
                books.append(book)

        print(f'[微信读书] 找到 {len(books)} 本书')
        return books

    except Exception as e:
        print(f'[微信读书] 搜索失败: {e}')
        return []


def search_jd(query):
    """京东图书搜索"""
    print(f'[京东] 搜索: {query}')
    books = []

    search_url = f'https://search.jd.com/Search?keyword={requests.utils.quote(query)}&enc=utf-8&wq={requests.utils.quote(query)}&pvid='
    headers = {**REQUEST_HEADERS, 'Referer': 'https://www.jd.com/'}

    try:
        resp = requests.get(search_url, headers=headers, timeout=6)
        resp.encoding = 'utf-8'
        if resp.status_code != 200:
            return []

        soup = BeautifulSoup(resp.text, 'lxml')
        items = soup.select('.gl-item') or soup.select('.gl-i-wrap')

        for item in items[:15]:
            try:
                book = {}
                title_el = item.select_one('.p-name em') or item.select_one('.p-name a')
                if title_el:
                    book['title'] = clean_text(title_el.get_text())

                author_el = item.select_one('.p-author a') or item.select_one('.p-author') or item.select_one('.p-shop')
                if author_el:
                    author_text = clean_text(author_el.get_text())
                    if author_text and not re.match(r'^京东', author_text):
                        book['author'] = author_text

                cover_el = item.select_one('.p-img img') or item.select_one('img')
                if cover_el:
                    src = cover_el.get('data-lazy-img') or cover_el.get('src') or ''
                    if src:
                        book['cover'] = src if src.startswith('http') else 'https:' + src

                sku_el = item.select_one('.p-img a') or item.select_one('.p-name a')
                if sku_el and sku_el.get('href'):
                    book['detail_url'] = sku_el['href'] if sku_el['href'].startswith('http') else 'https:' + sku_el['href']

                if book.get('title') and len(book['title']) > 2:
                    books.append(book)
            except Exception:
                continue

        print(f'[京东] 找到 {len(books)} 本书')
        return books
    except Exception as e:
        print(f'[京东] 搜索失败: {e}')
        return []


def search_dangdang(query):
    """当当图书搜索"""
    print(f'[当当] 搜索: {query}')
    books = []

    search_url = f'https://search.dangdang.com/?key={requests.utils.quote(query)}&act=input&filter=sub'

    try:
        resp = requests.get(search_url, headers=REQUEST_HEADERS, timeout=6)
        resp.encoding = 'utf-8'
        if resp.status_code != 200:
            return []

        soup = BeautifulSoup(resp.text, 'lxml')
        items = soup.select('.line') or soup.select('#component_59 li') or soup.select('li.line')

        for item in items[:15]:
            try:
                book = {}
                title_el = item.select_one('a')
                if title_el:
                    book['title'] = clean_text(title_el.get('title') or title_el.get_text())
                    href = title_el.get('href', '')
                    if href:
                        book['detail_url'] = href if href.startswith('http') else 'https://search.dangdang.com' + href

                cover_el = item.select_one('img')
                if cover_el:
                    src = cover_el.get('data-src') or cover_el.get('src') or ''
                    if src:
                        book['cover'] = src if src.startswith('http') else 'https:' + src

                author_el = item.select_one('.search_now_price') or item.select_one('.author')
                if author_el:
                    text = clean_text(author_el.get_text())
                    author_match = re.search(r'作者[:：]\s*([^/\n]+)', text)
                    if author_match:
                        book['author'] = clean_text(author_match.group(1))
                    elif text and len(text) < 30 and not re.match(r'^[¥￥]', text):
                        book['author'] = text.split('/')[0].strip()

                if not book.get('author') and title_el:
                    title_attr = title_el.get('title', '')
                    if title_attr:
                        parts = title_attr.split()
                        if len(parts) > 1 and len(parts[1]) < 20:
                            book['author'] = parts[1]

                if book.get('title') and len(book['title']) > 1:
                    books.append(book)
            except Exception:
                continue

        print(f'[当当] 找到 {len(books)} 本书')
        return books
    except Exception as e:
        print(f'[当当] 搜索失败: {e}')
        return []


def search_openlibrary(query):
    """Open Library API 搜索"""
    print(f'[Open Library] 搜索: {query}')
    books = []

    try:
        search_url = f'https://openlibrary.org/search.json?q={requests.utils.quote(query)}&limit=20'
        resp = requests.get(search_url, headers=REQUEST_HEADERS, timeout=7)
        if resp.status_code != 200:
            return []

        data = resp.json()
        for doc in data.get('docs', [])[:20]:
            book = {}
            book['title'] = doc.get('title', '')
            book['author'] = doc.get('author_name', [''])[0] if doc.get('author_name') else ''

            cover_i = doc.get('cover_i')
            if cover_i:
                book['cover'] = f'https://covers.openlibrary.org/b/id/{cover_i}-L.jpg'

            if doc.get('key'):
                book['detail_url'] = f'https://openlibrary.org{doc["key"]}'

            desc = ''
            if doc.get('first_sentence'):
                desc = doc['first_sentence'][0] if isinstance(doc['first_sentence'], list) else str(doc['first_sentence'])
            elif doc.get('subject'):
                desc = ', '.join(doc['subject'][:5])
            elif doc.get('edition_count'):
                desc = f"{doc.get('edition_count')}个版本"
            book['description'] = desc

            if book.get('title'):
                books.append(book)

        print(f'[Open Library] 找到 {len(books)} 本书')
        return books
    except Exception as e:
        print(f'[Open Library] 搜索失败: {e}')
        return []


def search_google_books(query):
    """Google Books API 搜索"""
    print(f'[Google Books] 搜索: {query}')
    books = []

    try:
        search_url = f'https://www.googleapis.com/books/v1/volumes?q={requests.utils.quote(query)}&maxResults=20'
        resp = requests.get(search_url, headers=REQUEST_HEADERS, timeout=6)
        if resp.status_code != 200:
            return []

        data = resp.json()
        for item in data.get('items', [])[:20]:
            vi = item.get('volumeInfo', {})
            book = {}
            book['title'] = vi.get('title', '')
            book['author'] = vi.get('authors', [''])[0] if vi.get('authors') else ''

            image_links = vi.get('imageLinks', {})
            if image_links.get('thumbnail'):
                book['cover'] = image_links['thumbnail']
            elif image_links.get('smallThumbnail'):
                book['cover'] = image_links['smallThumbnail']

            desc = vi.get('description', '')
            if desc:
                book['description'] = BeautifulSoup(desc, 'html.parser').get_text()[:300]

            if vi.get('infoLink'):
                book['detail_url'] = vi['infoLink']

            published = vi.get('publishedDate', '')
            if published:
                book['publishedYear'] = published[:4]

            if book.get('title'):
                books.append(book)

        print(f'[Google Books] 找到 {len(books)} 本书')
        return books
    except Exception as e:
        print(f'[Google Books] 搜索失败: {e}')
        return []


def merge_books(*book_lists):
    """合并多个来源的书籍，智能去重 + 信息合并 + 质量排序"""
    merged = {}

    for books in book_lists:
        for book in books:
            title = book.get('title', '').strip()
            if not title or len(title) < 1:
                continue

            key = re.sub(r'[\s\W]', '', title.lower())
            if not key:
                continue

            if key in merged:
                existing = merged[key]
                for field in ['author', 'cover', 'description', 'rating', 'detail_url', 'publishedYear', 'isbn']:
                    if not existing.get(field) and book.get(field):
                        existing[field] = book[field]
                sources = existing.get('_sources', set())
                if not isinstance(sources, set):
                    sources = set(sources)
                sources.add(book.get('_source', 'unknown'))
                existing['_sources'] = sources
                existing['_source_count'] = existing.get('_source_count', 1) + 1
            else:
                book_copy = dict(book)
                book_copy['_sources'] = {book.get('_source', 'unknown')}
                book_copy['_source_count'] = 1
                merged[key] = book_copy

    result = list(merged.values())

    def score(b):
        has_author = 1 if b.get('author') else 0
        has_cover = 1 if b.get('cover') else 0
        has_desc = 1 if b.get('description') else 0
        source_count = b.get('_source_count', 1)
        return has_author + has_cover + has_desc + source_count * 0.5

    result.sort(key=score, reverse=True)
    return result


def _book_score(b):
    has_author = 1 if b.get('author') else 0
    has_cover = 2 if b.get('cover') else 0  # 封面权重提高，优先选择有封面的书
    has_desc = 1 if b.get('description') else 0
    source_count = b.get('_source_count', 1)
    return has_author + has_cover + has_desc + source_count * 0.5


def _normalize_title(title):
    if not title:
        return ''
    t = title.lower()
    t = re.sub(r'[《〈<【\[（(]', '', t)
    t = re.sub(r'[》〉>】\]）)]', '', t)
    t = re.split(r'[:：—\-–]\s*', t)[0]
    t = re.sub(r'[^\u4e00-\u9fa5a-z0-9]', '', t)
    return t.strip()


# 简繁体常见字映射（作者名归一化用）
_SIMP_TRAD_MAP = str.maketrans('韓江東東陳張劉黃趙吳鄭謝郭洪周鄧曾朱羅梁宋許韓馮鄧彭蔣蔡賈魏盧閻沈姚潘金鐘謝譚鄒蘇石范方姚', '韩江东东陈张刘黄赵吴郑谢郭洪周邓曾朱罗梁宋许韩冯邓彭蒋蔡贾魏卢阎沈姚潘金钟谢谭邹苏石范方姚')


def _normalize_author(author):
    if not author:
        return ''
    a = author.strip()
    a = re.split(r'[/;,;；&]|\s+著|\s+编|\s+译| and ', a)[0].strip()
    a = re.sub(r'[\[【(（][\u4e00-\u9fa5a-zA-Z]{1,4}[\]】)）]', '', a)
    a = re.sub(r'[^\u4e00-\u9fa5a-zA-Z·]', '', a).strip()
    # 繁体转简体归一化（让 韓江/韩江 归为同一作者）
    a = a.translate(_SIMP_TRAD_MAP)
    return a.lower()


def filter_best_match(books, query=''):
    """
    按归一化书名分组（忽略作者差异，因简繁体/译者差异导致同书多版本）。
    同一书名只保留 score 最高的一本。
    若存在不同书名，优先返回与 query 最匹配的；最多3本。
    """
    if not books:
        return []

    # 按归一化书名分组（不再用 author 作为分组键，避免简繁体作者被拆分）
    groups = {}
    for book in books:
        title_key = _normalize_title(book.get('title', ''))
        if not title_key:
            continue
        if title_key not in groups or _book_score(book) > _book_score(groups[title_key]):
            groups[title_key] = book

    filtered = list(groups.values())

    # 排序：优先 query 完全匹配；其次 score 高；其次书名短（避免"素食者膳食指南"排在"素食者"前面）
    query_norm = _normalize_title(query)
    def match_score(b):
        title_norm = _normalize_title(b.get('title', ''))
        # 完全匹配 +10
        exact = 10 if title_norm == query_norm else 0
        # 以 query 开头 +5
        prefix = 5 if query_norm and title_norm.startswith(query_norm) and title_norm != query_norm else 0
        return exact + prefix + _book_score(b)

    filtered.sort(key=match_score, reverse=True)

    # 如果存在与 query 完全匹配的书名，只返回完全匹配的（可能有多个不同作者版本）
    if query_norm:
        exact_matches = [b for b in filtered if _normalize_title(b.get('title', '')) == query_norm]
        if exact_matches:
            # 完全匹配可能有多本（不同作者/译者版本），最多返回3本
            return exact_matches[:3]

    if len(filtered) <= 1:
        return filtered[:1]
    return filtered[:3]


def format_book_result(book):
    """转换为统一的前端可用格式"""
    sources_val = book.get('_sources', set())
    if isinstance(sources_val, set):
        sources_list = list(sources_val)
    else:
        sources_list = sources_val if sources_val else []

    return {
        'title': book.get('title', ''),
        'author': book.get('author', ''),
        'cover': book.get('cover', ''),
        'description': extract_first_n(book.get('description', book.get('intro', ''))),
        'rating': book.get('rating', ''),
        'detail_url': book.get('detail_url', ''),
        'publishedYear': book.get('publishedYear', ''),
        'source_count': book.get('_source_count', 1),
        'sources': sources_list
    }


def search_mq59(query):
    """宝阳悦读网 (mq59.com) 搜索 - 解析HTML页面结果"""
    print(f'[mq59] 搜索: {query}')
    books = []

    search_url = f'https://www.mq59.com/index/search/index.html?kw={requests.utils.quote(query)}'

    try:
        resp = requests.get(search_url, headers=REQUEST_HEADERS, timeout=8)
        resp.encoding = 'utf-8'
        if resp.status_code != 200:
            print(f'[mq59] HTTP {resp.status_code}')
            return []

        soup = BeautifulSoup(resp.text, 'html.parser')

        # 查找搜索结果链接
        results = soup.find_all('a', href=True)
        for a_tag in results:
            href = a_tag.get('href', '')
            text = a_tag.get_text(strip=True)
            
            # 匹配书籍详情链接格式
            if '/index/goods/detail.html' in href and text:
                # 解析文本格式：《书名》/作者 浏览人数
                title = ''
                author = ''
                
                # 尝试提取书名
                if '《' in text and '》' in text:
                    start = text.find('《') + 1
                    end = text.find('》')
                    if start < end:
                        title = text[start:end].strip()
                
                # 尝试提取作者（/后面的部分）
                if '/' in text:
                    parts = text.split('/')
                    if len(parts) >= 2:
                        author_part = parts[1].strip()
                        # 去掉浏览人数（格式如 "1906人浏览" 或 "浏览"）
                        # 先移除 "浏览" 相关内容
                        if '浏览' in author_part:
                            author_part = author_part.split('浏览')[0].strip()
                        # 再移除数字+人 格式（如 "1906人"）
                        author_part = re.sub(r'\d+人$', '', author_part).strip()
                        author = author_part
                        # 清理作者名中的多余空格
                        author = ' '.join(author.split())
                
                if not title:
                    title = text.split('/')[0].strip() if '/' in text else text
                
                if title and len(title) > 1:
                    book = {
                        'title': title,
                        'author': author,
                        'cover': '',  # mq59 搜索结果页没有封面
                        'description': '',
                        'detail_url': href if href.startswith('http') else f'https://www.mq59.com{href}'
                    }
                    books.append(book)
                    
                    if len(books) >= 20:
                        break

    except Exception as e:
        print(f'[mq59] 搜索异常: {e}')

    print(f'[mq59] 找到 {len(books)} 本书')
    return books


def search_amazon(query):
    """Amazon 搜索 - 使用简单页面解析"""
    print(f'[Amazon] 搜索: {query}')
    books = []

    # Amazon 搜索URL
    search_url = f'https://www.amazon.com/s?k={requests.utils.quote(query)}'

    try:
        # Amazon 需要更好的 headers
        amazon_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
        }
        
        resp = requests.get(search_url, headers=amazon_headers, timeout=8)
        resp.encoding = 'utf-8'
        if resp.status_code != 200:
            print(f'[Amazon] HTTP {resp.status_code}')
            return []

        soup = BeautifulSoup(resp.text, 'html.parser')

        # 查找搜索结果项
        # Amazon 使用 data-component-type="s-result-item" 标识结果
        result_items = soup.select('div[data-component-type="s-result-item"]')
        
        for item in result_items:
            try:
                book = {}
                
                # 提取标题
                title_el = item.select_one('h2 a span')
                if title_el:
                    book['title'] = title_el.get_text(strip=True)
                else:
                    # 尝试其他选择器
                    title_el = item.select_one('h2 span')
                    if title_el:
                        book['title'] = title_el.get_text(strip=True)
                    else:
                        continue  # 没有标题则跳过
                
                # 提取作者
                author_els = item.select('a[href*="s=booksellers"] span, .a-row.a-size-small span, .a-size-base:nth-of-type(2)')
                if not author_els:
                    # 尝试从信息区域提取
                    info_span = item.select('.a-row.a-size-small span')
                    if info_span:
                        book['author'] = info_span[0].get_text(strip=True)
                else:
                    book['author'] = author_els[0].get_text(strip=True)
                
                # 提取封面
                img_el = item.select_one('img.s-image')
                if img_el and img_el.get('src'):
                    book['cover'] = img_el['src']
                
                # 提取详情链接
                link_el = item.select_one('h2 a')
                if link_el and link_el.get('href'):
                    href = link_el['href']
                    book['detail_url'] = href if href.startswith('http') else f'https://www.amazon.com{href}'
                
                # 提取价格（可选）
                price_el = item.select_one('.a-price .a-offscreen')
                if price_el:
                    book['price'] = price_el.get_text(strip=True)
                
                if book.get('title') and len(book['title']) > 1:
                    books.append(book)
                    
                    if len(books) >= 20:
                        break
                        
            except Exception as e:
                continue

    except Exception as e:
        print(f'[Amazon] 搜索异常: {e}')

    print(f'[Amazon] 找到 {len(books)} 本书')
    return books


def search_baidu_baike(query):
    """百度百科搜索 - 主要获取作者和简介（不依赖封面）"""
    print(f'[百度百科] 搜索: {query}')
    books = []

    try:
        # 优先使用百度百科开放API
        api_url = 'https://baike.baidu.com/api/openapi/BaikeLemmaCardApi'
        params = {
            'scope': 10,
            'format': 'json',
            'appid': 42307,
            'bk_key': query,
            'bk_length': 400
        }
        resp = requests.get(api_url, params=params, headers=REQUEST_HEADERS, timeout=6)
        if resp.status_code == 200:
            try:
                data = resp.json()
            except Exception:
                data = {}

            if data.get('key'):
                abstract = data.get('abstract', '') or ''
                # 尝试从简介中提取作者
                author = ''
                if abstract:
                    # 模式1: "作者是XXX" / "作者为XXX"
                    m = re.search(r'作者[是为：:\s]+([^，。；\n、]+)', abstract)
                    if m:
                        author = m.group(1).strip()
                    # 模式2: "XXX著/编著/主编"
                    if not author:
                        m = re.search(r'([\u4e00-\u9fa5A-Za-z·\s]{2,20})(?:著|编著|主编|编写)', abstract)
                        if m:
                            author = m.group(1).strip()

                book = {
                    'title': data.get('key', query),
                    'author': author,
                    'description': extract_first_n(abstract, 300),
                    'cover': '',  # 百度百科不负责封面
                    'detail_url': data.get('url', f'https://baike.baidu.com/item/{requests.utils.quote(query)}'),
                    '_source': 'baike'
                }
                books.append(book)
                print(f'[百度百科] 找到词条: {data.get("key")}')
                return books

        # API失败时降级到搜索页解析
        search_url = f'https://baike.baidu.com/search?word={requests.utils.quote(query)}'
        resp = requests.get(search_url, headers=REQUEST_HEADERS, timeout=6)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            # 搜索结果的第一条摘要
            result = soup.select_one('.search-list-item') or soup.select_one('.result-list li')
            if result:
                summary_el = result.select_one('.abstract') or result.select_one('.summary') or result
                text = clean_text(summary_el.get_text())
                if text and len(text) > 10:
                    book = {
                        'title': query,
                        'author': '',
                        'description': extract_first_n(text, 300),
                        'cover': '',
                        '_source': 'baike'
                    }
                    books.append(book)
                    print(f'[百度百科] 找到搜索页结果')
    except Exception as e:
        print(f'[百度百科] 搜索异常: {e}')

    print(f'[百度百科] 共找到 {len(books)} 条')
    return books


def search_baidu_image(query):
    """百度图片搜索 - 获取书籍封面"""
    print(f'[百度图片] 搜索: {query}')
    covers = []

    try:
        keyword = f'{query} 书籍封面'
        api_url = 'https://image.baidu.com/search/acjson'
        # 精简参数 - 多余的参数会导致API返回空数据
        params = {
            'tn': 'resultjson_com',
            'logid': '12345',
            'word': keyword,
            'queryWord': keyword,
            'pn': 0,
            'rn': 10,
            'ie': 'utf-8',
            'oe': 'utf-8',
        }
        headers = {**REQUEST_HEADERS, 'Referer': 'https://image.baidu.com/'}
        resp = requests.get(api_url, params=params, headers=headers, timeout=6)
        if resp.status_code == 200:
            try:
                data = resp.json()
            except Exception:
                data = {}

            for item in data.get('data', []):
                if not item:
                    continue
                url = item.get('thumbURL') or item.get('middleURL') or item.get('hoverURL') or item.get('objURL')
                if not url or not url.startswith('http'):
                    continue
                # 过滤明显过小的图
                width = item.get('width') or 0
                height = item.get('height') or 0
                if width and height and (width < 100 or height < 100):
                    continue
                covers.append(url)
                if len(covers) >= 5:
                    break
    except Exception as e:
        print(f'[百度图片] 搜索异常: {e}')

    print(f'[百度图片] 找到 {len(covers)} 张图片')
    return covers


def search_bing_image(query):
    """Bing图片搜索 - 备用封面源"""
    print(f'[Bing图片] 搜索: {query}')
    covers = []

    try:
        keyword = f'{query} 书籍封面'
        search_url = f'https://www.bing.com/images/search?q={requests.utils.quote(keyword)}&first=1&count=8'
        resp = requests.get(search_url, headers=REQUEST_HEADERS, timeout=6)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            # Bing 图片有多种选择器，优先 mimg，再降级到其他
            img_els = soup.select('img.mimg') or soup.select('.imgpt img') or soup.select('.iusc')
            for el in img_els[:8]:
                src = el.get('src') or el.get('data-src') or el.get('data-mediaurl')
                if not src:
                    # 尝试从 m=json 属性解析
                    m_attr = el.get('m')
                    if m_attr:
                        try:
                            m_data = json.loads(m_attr)
                            src = m_data.get('murl') or m_data.get('turl')
                        except Exception:
                            pass
                if src and src.startswith('http'):
                    covers.append(src)
                if len(covers) >= 5:
                    break
    except Exception as e:
        print(f'[Bing图片] 搜索异常: {e}')

    print(f'[Bing图片] 找到 {len(covers)} 张图片')
    return covers


def is_valid_cover_url(url):
    """检查封面URL是否有效 - 过滤占位图、相对路径等"""
    if not url or not isinstance(url, str):
        return False
    if not url.startswith('http'):
        return False
    # 过滤明显的占位图/无图标记
    lower = url.lower()
    invalid_keywords = [
        'url_none', 'no-img', 'noimg', 'placeholder', 'default_cover',
        'no-book', 'nobook', 'blank', 'noimg', 'none.png', 'default.png',
        'placeholder.png', 'no-cover', 'nocover'
    ]
    for kw in invalid_keywords:
        if kw in lower:
            return False
    # 过滤相对路径（缺少http开头的）
    if not lower.startswith('http://') and not lower.startswith('https://'):
        return False
    return True


def _extract_core_keyword(title):
    """从书名中提取核心关键词 - 去除数字、标点、空白后的主要中文部分"""
    if not title:
        return ''
    # 去掉书名号、括号、冒号等
    clean = re.sub(r'[《》【】\[\]（）()【】：:·,，。.\-_/\\\s]+', ' ', title).strip()
    # 去掉纯数字
    parts = [p for p in clean.split() if not re.match(r'^[\d]+$', p)]
    if not parts:
        return ''
    # 选最长的部分作为核心关键词
    core = max(parts, key=len) if parts else ''
    # 如果核心词太短（如单字"三"），尝试用整个清洁后的书名
    if len(core) < 2 and len(clean) >= 2:
        return clean
    return core


def _is_chinese_text(text, min_ratio=0.5):
    """检查文本是否主要是中文 - 用于过滤乱码"""
    if not text:
        return False
    chinese_count = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    total = len(text)
    return chinese_count / max(total, 1) >= min_ratio


def _is_irrelevant_snippet(text, title=''):
    """检查简介是否明显无关 - 如"1是自然数"、"hao123是汇集"等"""
    if not text:
        return True
    irrelevant_patterns = [
        '汉语', '拼音', '汉字', '部首', '笔画',   # 汉字解释
        '是自然数', '是整数', '是最小的', '是有理数',  # 数字解释
        '是汇集', '网址导航', 'hao123', '上网导航',  # 网站介绍
        '百度百科', '搜狗百科',                 # 百科首页
    ]
    for p in irrelevant_patterns:
        if p in text:
            return True
    return False


def search_bing_snippet(title, author=''):
    """Bing搜索 - 获取书籍简介（用 site:douban.com 限定豆瓣结果，更精准）"""
    # 提取核心关键词，避免数字被单独搜索
    core = _extract_core_keyword(title)
    if not core or len(core) < 2:
        # 核心词太短，跳过搜索（避免误匹配）
        return ''

    # 构造查询关键词：site:douban.com 核心词 作者
    if author:
        author_clean = re.sub(r'[|｜].*$', '', author).strip()
        # 作者也要清理，去掉过短或纯数字的部分
        author_clean = author_clean.split()[0] if author_clean.split() else author_clean
        keyword = f'site:douban.com {core} {author_clean}'
    else:
        keyword = f'site:douban.com {core} 内容简介'

    print(f'[Bing搜索] 查询: {keyword}')
    try:
        resp = requests.get('https://www.bing.com/search',
                            params={'q': keyword, 'setlang': 'zh-CN'},
                            headers=REQUEST_HEADERS, timeout=6)
        if resp.status_code != 200:
            return ''

        soup = BeautifulSoup(resp.text, 'html.parser')
        algos = soup.select('.b_algo')
        if not algos:
            return ''

        core_lower = core.lower()
        author_lower = (author or '').lower()

        # 遍历前5条，找标题中包含核心词的那条
        for item in algos[:5]:
            h2 = item.select_one('h2 a')
            if not h2:
                continue
            item_title = h2.get_text(strip=True)
            # 标题中必须包含核心词
            if core_lower not in item_title.lower():
                continue
            p = item.select_one('p') or item.select_one('.b_caption p')
            if not p:
                continue
            text = clean_text(p.get_text())
            # 质量校验：长度、中文比例、相关性
            if len(text) < 20:
                continue
            if not _is_chinese_text(text, 0.4):
                continue
            if _is_irrelevant_snippet(text, title):
                continue
            # 简介最好包含核心词或作者名
            if core_lower in text.lower() or (author_lower and author_lower in text.lower()):
                return extract_first_n(text, 300)
            # 如果不包含，但标题匹配且质量过关，也接受
            return extract_first_n(text, 300)

        return ''
    except Exception as e:
        print(f'[Bing搜索] 异常: {e}')
        return ''


def fetch_desc_from_douban(title, author=''):
    """通过豆瓣 suggest API 搜索书名，找到匹配的书后访问详情页拿简介"""
    if not title or len(title) < 2:
        return ''

    try:
        api_url = 'https://book.douban.com/j/subject_suggest'
        params = {'q': title}
        headers = {
            **REQUEST_HEADERS,
            'Accept': 'application/json, text/plain, */*',
            'Referer': 'https://book.douban.com/',
        }
        resp = requests.get(api_url, params=params, headers=headers, timeout=6)
        if resp.status_code != 200:
            return ''

        data = resp.json()
        if not data:
            return ''

        # 找标题最匹配的候选
        title_clean = re.sub(r'[《》【】\[\]（）()：:·,，。.\-_\s]+', '', title).lower()
        best_match = None
        for item in data:
            if not item or item.get('type') != 'b':
                continue
            item_title = item.get('title', '').strip()
            # 去掉书名号
            if item_title.startswith('《') and item_title.endswith('》'):
                item_title = item_title[1:-1]
            item_title_clean = re.sub(r'[《》【】\[\]（）()：:·,，。.\-_\s]+', '', item_title).lower()
            # 精确匹配或包含关系
            if item_title_clean == title_clean:
                best_match = item
                break
            if title_clean in item_title_clean or item_title_clean in title_clean:
                if not best_match:
                    best_match = item

        if not best_match:
            return ''

        detail_url = best_match.get('url', '')
        if not detail_url:
            return ''

        # 访问详情页拿简介
        r = requests.get(detail_url, headers=headers, timeout=5)
        if r.status_code != 200:
            return ''

        soup = BeautifulSoup(r.text, 'html.parser')
        intro = soup.select_one('#link-report .intro') or soup.select_one('.intro')
        if intro:
            text = clean_text(intro.get_text())
            if text and len(text) > 20 and _is_chinese_text(text, 0.4):
                return extract_first_n(text, 300)
        return ''
    except Exception as e:
        print(f'[豆瓣Suggest兜底] 异常: {e}')
        return ''


def fill_missing_descriptions(books, max_fill=8):
    """并发为缺简介的书补充简介 - 优先豆瓣Suggest，Bing搜索兜底"""
    missing = [(i, b) for i, b in enumerate(books)
               if not b.get('description') or len(b.get('description', '')) < 10]
    if not missing:
        return

    missing = missing[:max_fill]
    print(f'[简介兜底] 为 {len(missing)} 本缺简介的书并发搜索')

    def fill_one(idx_book):
        idx, book = idx_book
        title = book.get('title', '')
        author = book.get('author', '')
        if not title:
            return idx, ''
        # 提取核心词，避免书名太长或带特殊字符
        core = _extract_core_keyword(title)
        if not core or len(core) < 2:
            return idx, ''
        # 优先用豆瓣Suggest
        desc = fetch_desc_from_douban(core, author)
        if not desc:
            # Bing搜索兜底
            desc = search_bing_snippet(title, author)
        return idx, desc

    filled = 0
    with ThreadPoolExecutor(max_workers=min(4, len(missing))) as executor:
        for idx, desc in executor.map(fill_one, missing):
            if desc and len(desc) > 10:
                books[idx]['description'] = desc
                books[idx]['_desc_from_search'] = True
                filled += 1
                print(f'  ✓ 已为「{books[idx]["title"]}」补充简介')
            else:
                print(f'  ✗ 「{books[idx]["title"]}」简介兜底失败')

    print(f'[简介兜底] 成功补充 {filled}/{len(missing)} 本')


def fill_missing_covers(books, max_fill=8):
    """并发为缺封面或无效封面的书补充图片 - 用每本书的title单独搜图"""
    # 不仅检查是否为空，还要检查是否是无效占位图
    missing = [(i, b) for i, b in enumerate(books) if not is_valid_cover_url(b.get('cover'))]
    # 清空无效封面字段
    for i, b in missing:
        b['cover'] = ''
    if not missing:
        return

    # 限制数量，避免过多请求
    missing = missing[:max_fill]
    print(f'[封面兜底] 为 {len(missing)} 本缺封面/无效封面的书并发搜图')

    def fill_one(idx_book):
        idx, book = idx_book
        title = book.get('title', '')
        if not title or len(title) < 1:
            return idx, None
        # 优先百度图片
        covers = search_baidu_image(title)
        if not covers:
            # Bing兜底
            covers = search_bing_image(title)
        if covers:
            return idx, covers[0]
        return idx, None

    filled = 0
    with ThreadPoolExecutor(max_workers=min(4, len(missing))) as executor:
        for idx, cover in executor.map(fill_one, missing):
            if cover:
                books[idx]['cover'] = cover
                books[idx]['_cover_from_search'] = True
                filled += 1
                print(f'  ✓ 已为「{books[idx]["title"]}」补充封面')
            else:
                print(f'  ✗ 「{books[idx]["title"]}」封面兜底失败')

    print(f'[封面兜底] 成功补充 {filled}/{len(missing)} 本')


def search_douban_suggest(query):
    """豆瓣 suggest API + 搜索页 - 主搜索源
    1. 先调 suggest API 拿JSON结构化数据
    2. 如果 suggest 结果少于5本，补充解析搜索页获取更多 subject 链接
    3. 并发抓取每本书的详情页拿简介
    """
    print(f'[豆瓣Suggest] 搜索: {query}')
    books = []
    seen_ids = set()

    headers = {
        **REQUEST_HEADERS,
        'Accept': 'application/json, text/plain, */*',
        'Referer': 'https://book.douban.com/',
    }

    try:
        # ===== 第一步：suggest API =====
        api_url = 'https://book.douban.com/j/subject_suggest'
        params = {'q': query}
        resp = requests.get(api_url, params=params, headers=headers, timeout=6)
        if resp.status_code == 200:
            try:
                data = resp.json()
            except Exception:
                data = []
        else:
            data = []

        candidates = []
        for item in (data or []):
            if not item or item.get('type') != 'b':
                continue
            title = item.get('title', '').strip()
            if title.startswith('《') and title.endswith('》'):
                title = title[1:-1]
            if not title:
                continue
            cover = item.get('pic', '')
            if cover and '/s/public/' in cover:
                cover = cover.replace('/s/public/', '/l/public/')
            sid = item.get('id', '')
            if sid in seen_ids:
                continue
            seen_ids.add(sid)
            book = {
                'title': title,
                'author': item.get('author_name', ''),
                'cover': cover,
                'description': '',
                'detail_url': item.get('url', ''),
                'publishedYear': item.get('year', ''),
                '_source': 'douban_suggest',
                '_douban_id': sid,
            }
            candidates.append(book)
            books.append(book)

        print(f'[豆瓣Suggest] API返回 {len(candidates)} 本')

        # ===== 第二步：如果结果少于5本，补充解析搜索页 =====
        if len(candidates) < 5:
            try:
                search_url = 'https://search.douban.com/book/subject_search'
                r = requests.get(search_url,
                                params={'search_text': query, 'cat': '1001'},
                                headers={**headers, 'Accept': 'text/html'},
                                timeout=6)
                if r.status_code == 200:
                    # 搜索页中提取所有 book.douban.com/subject/xxx 链接
                    subject_ids = re.findall(r'book\.douban\.com/subject/(\d+)', r.text)
                    new_ids = [sid for sid in subject_ids if sid not in seen_ids]
                    # 去重并取前10个
                    new_ids = list(dict.fromkeys(new_ids))[:10]
                    print(f'[豆瓣Suggest] 搜索页发现 {len(new_ids)} 个新subject，解析详情页')

                    # 并发解析每个subject详情页
                    def parse_subject_page(sid):
                        url = f'https://book.douban.com/subject/{sid}/'
                        try:
                            r2 = requests.get(url, headers=headers, timeout=5)
                            if r2.status_code != 200:
                                return None
                            soup = BeautifulSoup(r2.text, 'html.parser')
                            # 标题
                            title_el = soup.select_one('#wrapper h1') or soup.select_one('h1')
                            title = ''
                            if title_el:
                                title = clean_text(title_el.get_text())
                                # 去掉书名号
                                if title.startswith('《') and title.endswith('》'):
                                    title = title[1:-1]
                            if not title:
                                return None
                            # 作者
                            author = ''
                            author_el = soup.select_one('#info a')
                            if author_el:
                                author = clean_text(author_el.get_text())
                            # 封面
                            cover = ''
                            img_el = soup.select_one('#mainpic img') or soup.select_one('#wrapper .nbg img')
                            if img_el:
                                cover = img_el.get('src', '') or ''
                            # 简介
                            desc = ''
                            intro = soup.select_one('#link-report .intro') or soup.select_one('.intro')
                            if intro:
                                text = clean_text(intro.get_text())
                                if text and len(text) > 20 and _is_chinese_text(text, 0.4):
                                    desc = extract_first_n(text, 300)
                            return {
                                'title': title,
                                'author': author,
                                'cover': cover,
                                'description': desc,
                                'detail_url': url,
                                'publishedYear': '',
                                '_source': 'douban_search',
                                '_douban_id': sid,
                            }
                        except Exception as e:
                            print(f'[豆瓣Suggest] subject/{sid} 解析失败: {e}')
                            return None

                    with ThreadPoolExecutor(max_workers=min(5, len(new_ids))) as executor:
                        for result in executor.map(parse_subject_page, new_ids):
                            if result and result.get('title'):
                                sid = result.get('_douban_id', '')
                                if sid not in seen_ids:
                                    seen_ids.add(sid)
                                    candidates.append(result)
                                    books.append(result)

                    print(f'[豆瓣Suggest] 搜索页补充后共 {len(books)} 本')
            except Exception as e:
                print(f'[豆瓣Suggest] 搜索页解析失败: {e}')

        # ===== 第三步：对缺简介的书并发抓取详情页 =====
        need_desc = [b for b in books if not b.get('description')]
        if need_desc:
            print(f'[豆瓣Suggest] {len(need_desc)} 本缺简介，开始并发抓取详情页')

            def fetch_desc(book):
                url = book.get('detail_url', '')
                if not url:
                    return
                try:
                    r = requests.get(url, headers=headers, timeout=5)
                    if r.status_code != 200:
                        return
                    soup = BeautifulSoup(r.text, 'html.parser')
                    intro = soup.select_one('#link-report .intro') or soup.select_one('.intro')
                    if intro:
                        text = clean_text(intro.get_text())
                        if text and len(text) > 20 and _is_chinese_text(text, 0.4):
                            book['description'] = extract_first_n(text, 300)
                except Exception as e:
                    print(f'[豆瓣Suggest] 详情页抓取失败: {e}')

            with ThreadPoolExecutor(max_workers=min(5, len(need_desc))) as executor:
                list(executor.map(fetch_desc, need_desc))

        filled = sum(1 for b in books if b.get('description'))
        print(f'[豆瓣Suggest] 简介抓取完成: {filled}/{len(books)} 本')

    except Exception as e:
        print(f'[豆瓣Suggest] 异常: {e}')

    print(f'[豆瓣Suggest] 共返回 {len(books)} 本')
    return books


def _search_with_source(func, query, source_name):
    """通用包装器：给每个结果加上_source标记"""
    try:
        results = func(query) or []
        for r in results:
            r['_source'] = source_name
        return results
    except Exception as e:
        print(f'[{source_name}] 异常: {e}')
        return []


@app.route('/api/search', methods=['GET'])
def search_books():
    """
    主搜索接口 - 分治聚合搜索

    策略：
    1. 文字源（title/author/description）: 豆瓣/微信读书/京东/当当/OpenLibrary/Google/mq59/Amazon/百度百科
    2. 图片源（cover）: 百度图片/Bing图片（为缺封面的书兜底补充）
    各字段击中一个源即可使用，不必强求一个源给全所有信息。
    """
    query = request.args.get('q', '').strip()
    sources = [s.strip() for s in request.args.get('sources', 'douban_suggest').split(',')]

    if not query:
        return jsonify({'success': False, 'error': '请输入书名'}), 400

    cache_key = f'{query}_{"|".join(sorted(sources))}'
    cached = load_cache(cache_key)
    if cached is not None:
        print(f'[缓存] 返回 {len(cached)} 本书')
        return jsonify({'success': True, 'source': 'cache', 'books': cached, 'from_cache': True})

    print(f'[搜索] 查询: {query}, 来源: {sources}')
    start_time = time.time()

    # ===== 第一步：文字源并发搜索 =====
    search_tasks = []
    # ===== 核心链路（用户指定流程）：豆瓣搜索页HTML → 解析 → 详情页 =====
    if 'douban_search_page' in sources or 'all' in sources or 'douban' in sources:
        search_tasks.append(('douban_search_page', search_douban_search_page))
    # ===== 兜底源（仅当 sources=all/指定时启用） =====
    if 'douban' in sources or 'all' in sources or 'douban_suggest' in sources:
        search_tasks.append(('douban_suggest', search_douban_suggest))
    if 'douban' in sources or 'all' in sources:
        search_tasks.append(('douban_simple', search_douban_simple))
    # 其他源（默认不启用，仅 sources=all 时启用，避免中文书场景的噪音与超时）
    if 'weread' in sources or 'all' in sources:
        search_tasks.append(('weread', search_weread))
    if 'jd' in sources or 'all' in sources:
        search_tasks.append(('jd', search_jd))
    if 'dangdang' in sources or 'all' in sources:
        search_tasks.append(('dangdang', search_dangdang))
    if 'openlibrary' in sources or 'all' in sources:
        search_tasks.append(('openlibrary', search_openlibrary))
    if 'google' in sources or 'all' in sources:
        search_tasks.append(('google', search_google_books))
    if 'mq59' in sources or 'all' in sources:
        search_tasks.append(('mq59', search_mq59))
    if 'amazon' in sources or 'all' in sources:
        search_tasks.append(('amazon', search_amazon))
    if 'baike' in sources or 'all' in sources:
        search_tasks.append(('baike', search_baidu_baike))

    all_book_lists = []
    max_workers = max(3, len(search_tasks))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_source = {
            executor.submit(_search_with_source, func, query, name): name
            for name, func in search_tasks
        }
        try:
            for future in as_completed(future_to_source, timeout=12):
                source_name = future_to_source[future]
                try:
                    result = future.result(timeout=6)
                    if result:
                        all_book_lists.append(result)
                except Exception as e:
                    print(f'[{source_name}] 执行失败/超时: {e}')
        except Exception:
            print('[聚合] 部分源超时，使用已获取的结果')
            for future, source_name in future_to_source.items():
                if future.done():
                    try:
                        result = future.result(timeout=1)
                        if result:
                            all_book_lists.append(result)
                    except Exception:
                        pass

    merged = merge_books(*all_book_lists) if all_book_lists else []
    best_books = filter_best_match(merged, query)
    top_books = [b for b in best_books if b.get('title')]

    # ===== 第二步：简介兜底 + 封面兜底 并行执行（省一半时间） =====
    with ThreadPoolExecutor(max_workers=2) as executor:
        f_desc = executor.submit(fill_missing_descriptions, top_books)
        f_cover = executor.submit(fill_missing_covers, top_books)
        # 等待两个兜底都完成（每个内部也有超时控制）
        f_desc.result(timeout=60)
        f_cover.result(timeout=60)

    results = [format_book_result(b) for b in top_books]

    elapsed = time.time() - start_time
    print(f'[完成] 共找到 {len(results)} 本书, 耗时 {elapsed:.2f}s')

    if results:
        save_cache(cache_key, results)

    return jsonify({
        'success': True,
        'source': 'live',
        'books': results,
        'total': len(results),
        'elapsed': round(elapsed, 2)
    })


@app.route('/api/cache/clear', methods=['POST'])
def clear_cache():
    """清除所有缓存"""
    count = 0
    for f in os.listdir(CACHE_DIR):
        if f.endswith('.json'):
            os.remove(os.path.join(CACHE_DIR, f))
            count += 1
    return jsonify({'success': True, 'cleared': count})



@app.route('/api/cover', methods=['GET'])
def proxy_cover():
    """图片代理 - 解决豆瓣等防盗链问题"""
    target_url = request.args.get('url', '')
    if not target_url or not target_url.startswith('http'):
        return jsonify({'error': 'invalid url'}), 400

    try:
        from urllib.parse import urlparse
        parsed = urlparse(target_url)
        referer = f'{parsed.scheme}://{parsed.netloc}/'
        resp = requests.get(target_url, headers={
            'User-Agent': REQUEST_HEADERS['User-Agent'],
            'Referer': referer,
        }, timeout=8)

        if resp.status_code == 200:
            content_type = resp.headers.get('Content-Type', 'image/jpeg')
            if 'image' not in content_type:
                content_type = 'image/jpeg'
            from flask import Response
            return Response(resp.content, content_type=content_type)
        else:
            return jsonify({'error': f'upstream {resp.status_code}'}), resp.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    cache_count = 0
    if os.path.exists(CACHE_DIR):
        cache_count = len([f for f in os.listdir(CACHE_DIR) if f.endswith('.json')])
    return jsonify({
        'status': 'ok',
        'cache_dir': CACHE_DIR,
        'cache_count': cache_count,
        'text_sources': ['douban_suggest', 'douban', 'weread', 'jd', 'dangdang', 'openlibrary', 'google', 'mq59', 'amazon', 'baike'],
        'image_sources': ['baidu_image', 'bing_image'],
        'strategy': 'divide_and_conquer'
    })


if __name__ == '__main__':
    print('=' * 60)
    print('📚 读书会图书搜索服务 - 分治聚合版')
    print('=' * 60)
    print('')
    print('📖 接口说明:')
    print('   主接口:  GET /api/search?q=书名 [&sources=douban_search_page|all]')
    print('   清缓存:  POST /api/cache/clear')
    print('   健康检查: GET /api/health')
    print('   图片代理:  GET /api/cover?url=图片地址')
    print('')
    print('� 文字源: 豆瓣 / 微信读书 / 京东 / 当当 / OpenLibrary / Google / mq59 / Amazon / 百度百科')
    print('🖼️ 图片源: 百度图片 / Bing图片（为缺封面书兜底）')
    print('⚡ 策略:   分治聚合 - 各字段击中一个源即可使用')
    print('')
    print('💡 示例:')
    print('   http://localhost:5000/api/search?q=三体')
    print('   http://localhost:5000/api/search?q=百年孤独&sources=douban,weread,baike')
    print('   http://localhost:5000/api/health')
    print('=' * 60)
    print('')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
