// 书单投票应用
class BookListApp {
    constructor() {
        this.currentUser = null;
        this.searchResults = [];
        this.selectedBooks = [];
        this.voteCount = 3;
        this.currentVoteList = null;

        // 后端 API 配置 (Flask 多源聚合服务) - 自动启用
        // 本地开发：用 localhost:5000；服务器同源部署：用相对路径（前端和后端同一域名/端口）
        const isLocalDev = location.hostname === 'localhost' || location.hostname === '127.0.0.1' || location.hostname === '';
        this.backendApiUrl = isLocalDev ? 'http://localhost:5000' : '';
        this.backendApiEnabled = true;
        this.coverColors = ['#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe', '#00f2fe', '#43e97b', '#38f9d7', '#fa709a', '#fee140', '#30cfd0', '#330867', '#a8edea', '#fed6e3', '#ff9a9e', '#fecfef'];
        // 本地书籍数据库作为后备
        this.localBooks = [
            // 中国文学
            { key: 'local_1', title: '三体', author: '刘慈欣', coverUrl: 'https://covers.openlibrary.org/b/isbn/9787536692930-S.jpg', snippet: '文化大革命如火如荼进行的同时，军方探寻外星文明的绝秘计划"红岸工程"取得了突破性进展。', publishedYear: '2008' },
            { key: 'local_2', title: '百年孤独', author: '加西亚·马尔克斯', coverUrl: 'https://covers.openlibrary.org/b/isbn/9780060883287-S.jpg', snippet: '马孔多小镇的百年兴衰史，布恩迪亚家族七代人的传奇故事。', publishedYear: '1967' },
            { key: 'local_3', title: '活着', author: '余华', coverUrl: 'https://covers.openlibrary.org/b/isbn/9787506365437-S.jpg', snippet: '主人公福贵历经人生的沧桑起伏，表达了作者对生命意义的深沉思考。', publishedYear: '1993' },
            { key: 'local_4', title: '红楼梦', author: '曹雪芹', coverUrl: 'https://covers.openlibrary.org/b/isbn/9787020002207-S.jpg', snippet: '中国古典四大名著之首，讲述了贾、史、王、薛四大家族的兴衰。', publishedYear: '1791' },
            { key: 'local_5', title: '西游记', author: '吴承恩', coverUrl: 'https://covers.openlibrary.org/b/isbn/9787020008735-S.jpg', snippet: '中国古典四大名著之一，讲述唐僧师徒四人西天取经的故事。', publishedYear: '1592' },
            { key: 'local_6', title: '平凡的世界', author: '路遥', coverUrl: 'https://covers.openlibrary.org/b/isbn/9787530216781-S.jpg', snippet: '以孙少安和孙少平两兄弟为中心，刻画了当时社会各阶层众多普通人的形象。', publishedYear: '1986' },
            { key: 'local_7', title: '围城', author: '钱钟书', coverUrl: 'https://covers.openlibrary.org/b/isbn/9787020024759-S.jpg', snippet: '以方鸿渐的生活为线索，描写了知识分子群像的讽刺小说。', publishedYear: '1947' },
            { key: 'local_8', title: '人间失格', author: '太宰治', coverUrl: 'https://covers.openlibrary.org/b/isbn/9780811216074-S.jpg', snippet: '一个青年如何在自我毁灭中寻找救赎的故事。', publishedYear: '1948' },
            { key: 'local_9', title: '白夜行', author: '东野圭吾', coverUrl: 'https://covers.openlibrary.org/b/isbn/9787544258609-S.jpg', snippet: '1973年，大阪一栋废弃建筑内发现一具男尸，嫌疑人之女雪穗和被害人之子亮司，从此走上了截然不同却又紧密相关的人生。', publishedYear: '1999' },
            { key: 'local_10', title: '解忧杂货店', author: '东野圭吾', coverUrl: 'https://covers.openlibrary.org/b/isbn/9787544270878-S.jpg', snippet: '一间神奇的杂货店，能跨越时空收到咨询信并给出回答。', publishedYear: '2012' },
            { key: 'local_11', title: '嫌疑人X的献身', author: '东野圭吾', coverUrl: 'https://covers.openlibrary.org/b/isbn/9787544255370-S.jpg', snippet: '一位天才数学家为邻居犯下的案件设下完美的不在场证明。', publishedYear: '2005' },
            { key: 'local_12', title: '沉默的大多数', author: '王小波', coverUrl: 'https://covers.openlibrary.org/b/isbn/9787544247672-S.jpg', snippet: '王小波的杂文精选集，用幽默的笔触探讨了诸多社会话题。', publishedYear: '1997' },
            { key: 'local_13', title: '黄金时代', author: '王小波', coverUrl: 'https://covers.openlibrary.org/b/isbn/9787544242699-S.jpg', snippet: '文革时期作为背景，讲述了王二和陈清扬的爱情故事。', publishedYear: '1992' },
            { key: 'local_14', title: '目送', author: '龙应台', coverUrl: 'https://covers.openlibrary.org/b/isbn/9787544245579-S.jpg', snippet: '一部关于亲情、成长与离别的散文集。', publishedYear: '2008' },
            { key: 'local_15', title: '文化苦旅', author: '余秋雨', coverUrl: 'https://covers.openlibrary.org/b/isbn/9787506339811-S.jpg', snippet: '通过游历中华文化遗迹，反思中国文化的命运。', publishedYear: '1992' },
            // 外国文学
            { key: 'local_16', title: '1984', author: '乔治·奥威尔', coverUrl: 'https://covers.openlibrary.org/b/isbn/9780451524935-S.jpg', snippet: '反乌托邦小说经典，描绘了一个极权主义下的未来世界。', publishedYear: '1949' },
            { key: 'local_17', title: '动物农场', author: '乔治·奥威尔', coverUrl: 'https://covers.openlibrary.org/b/isbn/9780451526342-S.jpg', snippet: '一部伟大的政治寓言，讲述动物们在农场建立理想国的故事。', publishedYear: '1945' },
            { key: 'local_18', title: '小王子', author: '圣埃克苏佩里', coverUrl: 'https://covers.openlibrary.org/b/isbn/9780156012195-S.jpg', snippet: '一部写给成年人的童话，关于爱、责任和成长的寓言故事。', publishedYear: '1943' },
            { key: 'local_19', title: '挪威的森林', author: '村上春树', coverUrl: 'https://covers.openlibrary.org/b/isbn/9780374222842-S.jpg', snippet: '一段关于失去、爱与成长的青春故事。', publishedYear: '1987' },
            { key: 'local_20', title: '追风筝的人', author: '卡勒德·胡赛尼', coverUrl: 'https://covers.openlibrary.org/b/isbn/9781594634749-S.jpg', snippet: '12岁的阿富汗富家少爷阿米尔与仆人哈桑情同手足，关于人性的背叛与救赎。', publishedYear: '2003' },
            { key: 'local_21', title: '基督山伯爵', author: '大仲马', coverUrl: 'https://covers.openlibrary.org/b/isbn/9780140449266-S.jpg', snippet: '一个被陷害的水手越狱后化名基督山伯爵，开始漫长的复仇之旅。', publishedYear: '1844' },
            { key: 'local_22', title: '悲惨世界', author: '维克多·雨果', coverUrl: 'https://covers.openlibrary.org/b/isbn/9780140444308-S.jpg', snippet: '法国大革命后，前囚犯冉阿让的救赎之旅。', publishedYear: '1862' },
            { key: 'local_23', title: '巴黎圣母院', author: '维克多·雨果', coverUrl: 'https://covers.openlibrary.org/b/isbn/9780140441062-S.jpg', snippet: '钟楼怪人卡西莫多与吉普赛少女爱斯美拉达的爱情悲剧。', publishedYear: '1831' },
            { key: 'local_24', title: '罪与罚', author: '陀思妥耶夫斯基', coverUrl: 'https://covers.openlibrary.org/b/isbn/9780143058144-S.jpg', snippet: '一个穷学生杀人后的内心挣扎与救赎。', publishedYear: '1866' },
            { key: 'local_25', title: '卡拉马佐夫兄弟', author: '陀思妥耶夫斯基', coverUrl: 'https://covers.openlibrary.org/b/isbn/9780140449242-S.jpg', snippet: '一部关于信仰、怀疑和人性的伟大哲学小说。', publishedYear: '1880' },
            { key: 'local_26', title: '战争与和平', author: '列夫·托尔斯泰', coverUrl: 'https://covers.openlibrary.org/b/isbn/9780140447936-S.jpg', snippet: '拿破仑时代俄国社会的宏伟画卷。', publishedYear: '1869' },
            { key: 'local_27', title: '安娜·卡列尼娜', author: '列夫·托尔斯泰', coverUrl: 'https://covers.openlibrary.org/b/isbn/9780140449174-S.jpg', snippet: '一段关于爱情、家庭与社会的悲剧。', publishedYear: '1877' },
            { key: 'local_28', title: '傲慢与偏见', author: '简·奥斯汀', coverUrl: 'https://covers.openlibrary.org/b/isbn/9780141439518-S.jpg', snippet: '伊丽莎白·班纳特与达西先生的爱情故事。', publishedYear: '1813' },
            { key: 'local_29', title: '爱玛', author: '简·奥斯汀', coverUrl: 'https://covers.openlibrary.org/b/isbn/9780141439662-S.jpg', snippet: '爱玛·伍德豪斯的爱情冒险与成长。', publishedYear: '1815' },
            { key: 'local_30', title: '简爱', author: '夏洛蒂·勃朗特', coverUrl: 'https://covers.openlibrary.org/b/isbn/9780142437209-S.jpg', snippet: '一个孤儿女教师的独立与爱情。', publishedYear: '1847' },
            // 现代畅销
            { key: 'local_31', title: '哈利·波特与魔法石', author: 'J.K.罗琳', coverUrl: 'https://covers.openlibrary.org/b/isbn/9780590353427-S.jpg', snippet: '11岁的哈利·波特收到霍格沃茨魔法学校的录取通知书，开启了一段奇妙的魔法之旅。', publishedYear: '1997' },
            { key: 'local_32', title: '达·芬奇密码', author: '丹·布朗', coverUrl: 'https://covers.openlibrary.org/b/isbn/9780307474278-S.jpg', snippet: '卢浮宫馆长的离奇死亡，牵出一段隐藏多年的宗教秘密。', publishedYear: '2003' },
            { key: 'local_33', title: '失落的秘符', author: '丹·布朗', coverUrl: 'https://covers.openlibrary.org/b/isbn/9780307474278-S.jpg', snippet: '罗伯特·兰登教授再次踏上解谜之旅，这次是在华盛顿特区。', publishedYear: '2009' },
            { key: 'local_34', title: '饥饿游戏', author: '苏珊·柯林斯', coverUrl: 'https://covers.openlibrary.org/b/isbn/9780439023528-S.jpg', snippet: '在被分为12个区的帕南姆，每年每个区必须派出两名青少年参加饥饿游戏。', publishedYear: '2008' },
            { key: 'local_35', title: '暮光之城', author: '斯蒂芬妮·梅耶', coverUrl: 'https://covers.openlibrary.org/b/isbn/9780316015844-S.jpg', snippet: '人类女孩贝拉与吸血鬼爱德华的禁忌之恋。', publishedYear: '2005' },
            { key: 'local_36', title: '冰与火之歌', author: '乔治·R·R·马丁', coverUrl: 'https://covers.openlibrary.org/b/isbn/9780553108033-S.jpg', snippet: '七国争霸的史诗巨著，权力的游戏。', publishedYear: '1996' },
            { key: 'local_37', title: '魔戒', author: 'J.R.R.托尔金', coverUrl: 'https://covers.openlibrary.org/b/isbn/9780261103207-S.jpg', snippet: '年轻的霍比特人佛罗多踏上销毁至尊魔戒的征途。', publishedYear: '1954' },
            { key: 'local_38', title: '霍比特人', author: 'J.R.R.托尔金', coverUrl: 'https://covers.openlibrary.org/b/isbn/9780547928227-S.jpg', snippet: '比尔博·巴金斯被卷入一场争夺龙族宝藏的冒险。', publishedYear: '1937' },
            // 哲学/思想
            { key: 'local_39', title: '查拉图斯特拉如是说', author: '尼采', coverUrl: 'https://covers.openlibrary.org/b/isbn/9780140441130-S.jpg', snippet: '尼采最具代表性的作品，以诗般的语言阐述哲学思想。', publishedYear: '1883' },
            { key: 'local_40', title: '存在与时间', author: '海德格尔', coverUrl: 'https://covers.openlibrary.org/b/isbn/9780060638285-S.jpg', snippet: '二十世纪最具影响力的哲学著作之一。', publishedYear: '1927' },
            { key: 'local_41', title: '西西弗神话', author: '加缪', coverUrl: 'https://covers.openlibrary.org/b/isbn/9780679720201-S.jpg', snippet: '关于荒诞哲学的重要论著。', publishedYear: '1942' },
            { key: 'local_42', title: '鼠疫', author: '加缪', coverUrl: 'https://covers.openlibrary.org/b/isbn/9780679720201-S.jpg', snippet: '奥兰城爆发鼠疫，人们在死亡面前表现出的各种态度。', publishedYear: '1947' },
            { key: 'local_43', title: '局外人', author: '加缪', coverUrl: 'https://covers.openlibrary.org/b/isbn/9780679720201-S.jpg', snippet: '一个"局外人"的视角，展示世界的荒诞。', publishedYear: '1942' },
            // 中国现代/当代
            { key: 'local_44', title: '朝花夕拾', author: '鲁迅', coverUrl: 'https://covers.openlibrary.org/b/isbn/9787020024759-S.jpg', snippet: '鲁迅的回忆性散文集，记录了他的童年和青年时代。', publishedYear: '1928' },
            { key: 'local_45', title: '呐喊', author: '鲁迅', coverUrl: 'https://covers.openlibrary.org/b/isbn/9787020024759-S.jpg', snippet: '鲁迅的短篇小说集，包含《狂人日记》《阿Q正传》等名篇。', publishedYear: '1923' },
            { key: 'local_46', title: '彷徨', author: '鲁迅', coverUrl: 'https://covers.openlibrary.org/b/isbn/9787020024759-S.jpg', snippet: '鲁迅的第二本小说集，深刻揭示了国民性问题。', publishedYear: '1926' },
            { key: 'local_47', title: '茶馆', author: '老舍', coverUrl: 'https://covers.openlibrary.org/b/isbn/9787020024759-S.jpg', snippet: '通过一个茶馆的兴衰，展现了清末民初的社会变迁。', publishedYear: '1957' },
            { key: 'local_48', title: '骆驼祥子', author: '老舍', coverUrl: 'https://covers.openlibrary.org/b/isbn/9787020024759-S.jpg', snippet: '一个人力车夫祥子的悲剧人生。', publishedYear: '1929' },
            { key: 'local_49', title: '边城', author: '沈从文', coverUrl: 'https://covers.openlibrary.org/b/isbn/9787020024759-S.jpg', snippet: '湘西茶峒小城翠翠的纯美爱情故事。', publishedYear: '1934' },
            { key: 'local_50', title: '围城', author: '钱钟书', coverUrl: 'https://covers.openlibrary.org/b/isbn/9787020024759-S.jpg', snippet: '以方鸿渐的生活为线索，描写了知识分子群像的讽刺小说。', publishedYear: '1947' }
        ];
        this.loadUser();
        this.initEvents();
    }

    // 加载用户
    loadUser() {
        const savedUser = localStorage.getItem('booklist_user');
        if (savedUser) {
            this.currentUser = savedUser;
            this.showMainApp();
        }
    }

    // 保存用户
    saveUser(name) {
        localStorage.setItem('booklist_user', name);
        this.currentUser = name;
    }

    // 显示主应用
    showMainApp() {
        document.getElementById('loginScreen').classList.add('hidden');
        document.getElementById('mainApp').classList.remove('hidden');
        document.getElementById('currentUserName').textContent = this.currentUser;
        this.loadMyLists();
        this.loadAvailableLists();
    }

    // 初始化事件
    initEvents() {
        // 登录
        document.getElementById('enterBtn').addEventListener('click', () => this.handleLogin());
        document.getElementById('userName').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.handleLogin();
        });

        // 导航标签
        document.querySelectorAll('.nav-tab').forEach(tab => {
            tab.addEventListener('click', () => this.switchTab(tab.dataset.tab));
        });

        // 搜索书籍
        document.getElementById('searchBtn').addEventListener('click', () => this.searchBooks());
        document.getElementById('searchInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.searchBooks();
        });

        // 投票数量选择
        document.querySelectorAll('.count-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.count-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.voteCount = parseInt(btn.dataset.count);
                document.getElementById('customCount').value = '';
            });
        });

        // 自定义投票数量
        document.getElementById('customCount').addEventListener('input', (e) => {
            const val = parseInt(e.target.value);
            if (val >= 1 && val <= 10) {
                this.voteCount = val;
                document.querySelectorAll('.count-btn').forEach(b => b.classList.remove('active'));
            }
        });

        // 创建书单
        document.getElementById('createListBtn').addEventListener('click', () => this.createList());

        // 加入投票
        document.getElementById('joinByCodeBtn').addEventListener('click', () => this.joinByCode());

        // 提交投票
        document.getElementById('submitVoteBtn').addEventListener('click', () => this.submitVote());

        // 选择书单查看结果
        document.getElementById('resultListSelect').addEventListener('change', (e) => {
            if (e.target.value) this.showResult(e.target.value);
        });

        // 二维码弹窗
        document.getElementById('closeQrBtn').addEventListener('click', () => {
            document.getElementById('qrModal').classList.add('hidden');
        });
        document.getElementById('copyCodeBtn').addEventListener('click', () => this.copyListCode());

        // 书籍详情弹窗

        document.getElementById('closeDetailBtn').addEventListener('click', () => {
            document.getElementById('bookDetailModal').classList.add('hidden');
        });

        // 手动添加书籍
        document.getElementById('manualCover').addEventListener('change', (e) => this.handleCoverUpload(e));
        document.getElementById('confirmManualAddBtn').addEventListener('click', () => this.confirmManualAdd());
        document.getElementById('cancelManualAddBtn').addEventListener('click', () => {
            document.getElementById('manualAddModal').classList.add('hidden');
        });
    }

    // 处理登录
    handleLogin() {
        const nameInput = document.getElementById('userName');
        const errorMsg = document.getElementById('nameError');
        const name = nameInput.value.trim();

        if (!name) {
            errorMsg.textContent = '请输入名字';
            return;
        }

        if (name.length > 10) {
            errorMsg.textContent = '名字最多10个字';
            return;
        }

        this.saveUser(name);
        this.showMainApp();
    }

    // 切换标签
    switchTab(tabName) {
        document.querySelectorAll('.nav-tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.tab === tabName);
        });
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.toggle('active', content.id === `${tabName}Tab`);
        });

        if (tabName === 'result') {
            this.loadResultLists();
        } else if (tabName === 'my') {
            this.loadMyLists();
        } else if (tabName === 'vote') {
            this.loadAvailableLists();
        }
    }

    // 搜索书籍 - 并发多源聚合版
    async searchBooks() {
        const query = document.getElementById('searchInput').value.trim();
        const resultsDiv = document.getElementById('searchResults');

        if (!query) {
            this.showToast('请输入书名');
            return;
        }

        resultsDiv.innerHTML = '<div class="loading" style="text-align:center;padding:20px;"><div class="spinner"></div><p>🔍 多源并发搜索中...</p></div>';

        // 1. 检查本地缓存
        const cachedResults = this.getSearchCache(query);
        if (cachedResults && cachedResults.length > 0) {
            this.searchResults = cachedResults;
            this.renderSearchResults();
            this.showToast(`📦 从缓存加载 ${cachedResults.length} 本书`);
            return;
        }

        // 2. 本地书籍数据库（快速命中经典书）
        const localResults = this.localBooks.filter(book =>
            book.title.toLowerCase().includes(query.toLowerCase()) ||
            book.author.toLowerCase().includes(query.toLowerCase())
        );

        // 启动所有搜索源（并发，谁先返回谁先显示）
        const searchPromises = [];

        // 2a. 本地后端聚合服务（最优先，一次返回所有源的合并结果）
        if (this.backendApiEnabled && this.backendApiUrl) {
            searchPromises.push({
                name: 'backend',
                promise: this.fetchWithTimeout(`${this.backendApiUrl}/api/search?q=${encodeURIComponent(query)}`, {
                    headers: { 'Accept': 'application/json' }
                }, 60000).then(r => r.json()).then(data => ({
                    source: 'backend',
                    books: (data.books || []).map((book, index) => ({
                        key: 'backend_' + index + '_' + Date.now(),
                        title: book.title || '未知书名',
                        author: book.author || '未知作者',
                        coverUrl: book.cover || null,
                        snippet: book.description || '',
                        publishedYear: book.publishedYear || '',
                        sourceCount: book.source_count || 1,
                        sources: book.sources || []
                    })),
                    total: data.total || 0,
                    elapsed: data.elapsed || 0
                })).catch(e => ({ source: 'backend', books: [], error: e.message }))
            });
        }

        // 2b. Open Library API
        searchPromises.push({
            name: 'openlibrary',
            promise: this.fetchWithTimeout(`https://openlibrary.org/search.json?q=${encodeURIComponent(query)}&limit=20`, {}, 5000)
                .then(r => r.json())
                .then(data => ({
                    source: 'openlibrary',
                    books: (data.docs || []).map(doc => ({
                        key: 'ol_' + doc.key,
                        title: doc.title,
                        author: doc.author_name ? doc.author_name[0] : '未知作者',
                        coverUrl: doc.cover_i ? `https://covers.openlibrary.org/b/id/${doc.cover_i}-L.jpg` : null,
                        snippet: doc.first_sentence ? doc.first_sentence[0] : (doc.subject ? doc.subject.slice(0, 3).join(', ') : ''),
                        publishedYear: doc.first_publish_year || ''
                    }))
                })).catch(() => ({ source: 'openlibrary', books: [] }))
        });

        // 2c. Google Books API
        searchPromises.push({
            name: 'google',
            promise: this.fetchWithTimeout(`https://www.googleapis.com/books/v1/volumes?q=${encodeURIComponent(query)}&maxResults=20`, {}, 5000)
                .then(r => r.json())
                .then(data => ({
                    source: 'google',
                    books: (data.items || []).map(item => ({
                        key: 'google_' + item.id,
                        title: item.volumeInfo.title,
                        author: item.volumeInfo.authors ? item.volumeInfo.authors[0] : '未知作者',
                        coverUrl: item.volumeInfo.imageLinks ? (item.volumeInfo.imageLinks.thumbnail || item.volumeInfo.imageLinks.smallThumbnail) : null,
                        snippet: item.volumeInfo.description ? item.volumeInfo.description.replace(/<[^>]+>/g, '').substring(0, 200) : '',
                        publishedYear: item.volumeInfo.publishedDate ? item.volumeInfo.publishedDate.substring(0, 4) : ''
                    }))
                })).catch(() => ({ source: 'google', books: [] }))
        });

        // 并发执行所有搜索
        let allResults = [];
        let totalFound = 0;

        try {
            const results = await Promise.all(searchPromises.map(p => p.promise));
            
            for (const r of results) {
                if (r.books && r.books.length > 0) {
                    totalFound += r.books.length;
                    
                    if (r.source === 'backend') {
                        // 后端已是聚合结果，直接用
                        allResults = allResults.concat(r.books);
                    } else {
                        allResults = allResults.concat(r.books);
                    }
                }
            }
        } catch (e) {
            console.error('搜索异常:', e);
        }

        // 与本地书籍合并
        if (localResults.length > 0) {
            allResults = localResults.slice(0, 10).concat(allResults);
        }

        // 前端去重（按标题）
        const seen = new Set();
        const uniqueResults = [];
        for (const book of allResults) {
            const key = (book.title || '').toLowerCase().trim();
            if (key && !seen.has(key)) {
                seen.add(key);
                uniqueResults.push(book);
            }
        }

        this.searchResults = uniqueResults;
        
        if (uniqueResults.length > 0) {
            this.saveSearchCache(query, uniqueResults);
            this.renderSearchResults();
            this.showToast(`✨ 从多源找到 ${uniqueResults.length} 本书`);
        } else {
            resultsDiv.innerHTML = '';
            this.searchResults = [];
            this.renderSearchResults();
            // 无结果时，显示本地数据库的相关推荐
            const keyword = query.toLowerCase();
            const fuzzyResults = this.localBooks.filter(book => {
                const titleLower = book.title.toLowerCase();
                const authorLower = book.author.toLowerCase();
                // 模糊匹配：书名或作者包含关键词的一部分
                return titleLower.includes(keyword.substring(0, 2)) ||
                       authorLower.includes(keyword.substring(0, 2)) ||
                       titleLower.split('').some(c => keyword.includes(c));
            }).slice(0, 5);

            let fuzzyHtml = '';
            if (fuzzyResults.length > 0) {
                fuzzyHtml = `<div style="margin-top:20px;padding:15px;background:#f7fafc;border-radius:8px;"><p style="font-size:0.9rem;color:#4a5568;margin-bottom:10px;">📚 本地书单推荐：</p>` +
                    fuzzyResults.map(book => this.renderBookCard(book)).join('') +
                    '</div>';
            }

            // 保存当前搜索词，供手动添加使用
            this.lastSearchQuery = query;
            resultsDiv.innerHTML += 
                `<div style="text-align:center;padding:20px;color:#718096;">
                    <p>😢 在线API未找到"${this.escapeHtml(query)}"</p>
                    <p style="font-size:0.85rem;">💡 提示：</p>
                    <ul style="text-align:left;font-size:0.85rem;color:#4a5568;margin:10px auto;max-width:280px;line-height:1.6;">
                        <li>检查拼写是否正确</li>
                        <li>尝试更简短的关键词</li>
                        <li>确认本地后端服务已启动 (http://localhost:5000)</li>
                    </ul>
                    <button class="btn primary" style="margin-top:12px;" onclick="app.openManualAdd()">✏️ 手动添加这本书</button>
                </div>` + fuzzyHtml;
        }
    }

    // 获取搜索缓存
    getSearchCache(query) {
        try {
            const cache = localStorage.getItem('booklist_search_cache');
            if (cache) {
                const cacheData = JSON.parse(cache);
                const key = query.toLowerCase().trim();
                if (cacheData[key] && cacheData[key].results && cacheData[key].results.length > 0) {
                    // 检查缓存有效期（24小时）
                    const now = Date.now();
                    if (now - cacheData[key].timestamp < 24 * 60 * 60 * 1000) {
                        return cacheData[key].results;
                    }
                }
            }
        } catch (e) {
            console.warn('读取缓存失败:', e);
        }
        return null;
    }

    // 保存搜索缓存
    saveSearchCache(query, results) {
        try {
            const cache = localStorage.getItem('booklist_search_cache');
            let cacheData = {};
            if (cache) {
                cacheData = JSON.parse(cache);
            }
            const key = query.toLowerCase().trim();
            cacheData[key] = {
                results: results,
                timestamp: Date.now()
            };
            localStorage.setItem('booklist_search_cache', JSON.stringify(cacheData));
        } catch (e) {
            console.warn('保存缓存失败:', e);
        }
    }



    // 渲染单个书籍卡片（可复用）
    renderBookCard(book, showAddBtn = true) {
        const key = book.key || ('local_' + book.title + '_' + Date.now());
        const sourceCount = book.sourceCount || 1;
        const sourceBadge = sourceCount > 1 
            ? `<span class="source-badge" title="该书在${sourceCount}个数据源中都存在">✅ ${sourceCount}源</span>` 
            : '';
        const addBtn = showAddBtn 
            ? `<button class="btn-add" onclick="event.stopPropagation();app.addBookToList('${key}')">+ 添加</button>`
            : '';
        
        return `
        <div class="search-result-item" onclick="app.selectBook('${key}')">
            ${book.coverUrl 
                ? `<div class="cover-wrapper">
                     ${this.renderCoverImg(book, true)}
                     ${this.generatePlaceholderCover(book)}
                   </div>`
                : `<div class="cover-wrapper">${this.generatePlaceholderCover(book)}</div>`
            }
            <div class="result-info">
                <div class="result-title">${this.escapeHtml(book.title)}${sourceBadge}</div>
                <div class="result-author">${this.escapeHtml(book.author)}</div>
                ${book.snippet ? `<div class="result-snippet">${this.escapeHtml(book.snippet.substring(0, 100))}${book.snippet.length > 100 ? '...' : ''}</div>` : ''}
            </div>
            ${addBtn}
        </div>
    `;
    }

    // 渲染搜索结果
    renderSearchResults() {
        const resultsDiv = document.getElementById('searchResults');
        
        if (this.searchResults.length === 0) {
            resultsDiv.innerHTML = '<p style="text-align:center;padding:20px;color:#718096;">未找到相关书籍</p>';
            return;
        }

        resultsDiv.innerHTML = this.searchResults.map(book => this.renderBookCard(book)).join('');
        // 添加提示
        resultsDiv.innerHTML += '<p class="search-hint" onclick="app.addFirstResult()">👆 点击添加第一本书到书单</p>';
    }

    // 添加第一本书到书单
    addFirstResult() {
        if (this.searchResults.length === 0) {
            this.showToast('没有可添加的书籍');
            return;
        }
        const firstBook = this.searchResults[0];
        this.selectBook(firstBook.key);
        this.showToast(`已添加《${firstBook.title}》到书单`);
    }

    selectBook(key) {
        // 先从搜索结果中找
        let book = this.searchResults.find(b => b.key === key);
        // 如果没找到，从选中列表或本地书籍中找
        if (!book) {
            book = this.selectedBooks.find(b => b.key === key);
        }
        if (!book) {
            // 生成一个临时书籍对象
            book = { key: key, title: '未知书籍', author: '未知作者', snippet: '' };
        }

        if (this.selectedBooks.find(b => b.key === key)) {
            this.showToast('该书已在书单中');
            return;
        }

        this.selectedBooks.push(book);
        this.renderSelectedBooks();
        this.showToast(`已添加：${book.title}`);
    }

    addBookToList(key) {
        this.selectBook(key);
    }

    // 打开手动添加书籍界面
    openManualAdd() {
        const title = this.lastSearchQuery || '';
        document.getElementById('manualTitle').value = title;
        document.getElementById('manualAuthor').value = '';
        document.getElementById('manualDescription').value = '';
        document.getElementById('manualCover').value = '';
        
        // 重置封面预览为纯色占位符
        this.resetCoverPreview(title);
        
        // 保存上传的封面数据
        this.manualCoverData = null;
        
        document.getElementById('manualAddModal').classList.remove('hidden');
    }

    // 重置封面预览为纯色占位符
    resetCoverPreview(title) {
        const placeholder = document.getElementById('coverPreviewPlaceholder');
        const colorIndex = (title.charCodeAt(0) || 0) % this.coverColors.length;
        const bgColor = this.coverColors[colorIndex];
        const nextColor = this.coverColors[(colorIndex + 5) % this.coverColors.length];
        
        placeholder.style.background = `linear-gradient(135deg, ${bgColor}, ${nextColor})`;
        placeholder.style.color = '#fff';
        placeholder.style.fontSize = '0.9rem';
        placeholder.style.fontWeight = 'bold';
        placeholder.textContent = title ? title.substring(0, 6) : '封面预览';
    }

    // 处理封面上传
    handleCoverUpload(e) {
        const file = e.target.files[0];
        if (!file) {
            this.manualCoverData = null;
            this.resetCoverPreview(document.getElementById('manualTitle').value);
            return;
        }

        // 检查文件大小（限制 2MB）
        if (file.size > 2 * 1024 * 1024) {
            this.showToast('图片不能超过2MB');
            e.target.value = '';
            return;
        }

        const reader = new FileReader();
        reader.onload = (event) => {
            this.manualCoverData = event.target.result;
            // 显示预览
            const preview = document.getElementById('coverPreview');
            const placeholder = document.getElementById('coverPreviewPlaceholder');
            placeholder.innerHTML = `<img src="${event.target.result}" alt="封面预览">`;
            placeholder.style.background = 'none';
        };
        reader.readAsDataURL(file);
    }

    // 确认手动添加
    confirmManualAdd() {
        const title = document.getElementById('manualTitle').value.trim();
        const author = document.getElementById('manualAuthor').value.trim();

        if (!title) {
            this.showToast('书名不能为空');
            return;
        }
        if (!author) {
            this.showToast('请输入作者');
            return;
        }

        // 检查是否已在书单中
        const existingKey = 'manual_' + title + '_' + Date.now();
        if (this.selectedBooks.find(b => b.title === title)) {
            this.showToast('该书已在书单中');
            document.getElementById('manualAddModal').classList.add('hidden');
            return;
        }

        const book = {
            key: existingKey,
            title: title,
            author: author,
            coverUrl: this.manualCoverData || null,
            snippet: document.getElementById('manualDescription').value.trim(),
            publishedYear: '',
            isManual: true
        };

        this.selectedBooks.push(book);
        this.renderSelectedBooks();
        this.showToast(`已添加：${title}`);
        document.getElementById('manualAddModal').classList.add('hidden');
    }

    // 移除书籍
    removeBook(key) {
        this.selectedBooks = this.selectedBooks.filter(b => b.key !== key);
        this.renderSelectedBooks();
    }

    // 渲染已选书籍
    renderSelectedBooks() {
        const container = document.getElementById('selectedBooks');
        
        if (this.selectedBooks.length === 0) {
            container.innerHTML = '<p class="hint">点击搜索结果添加到书单</p>';
            return;
        }

        container.innerHTML = this.selectedBooks.map(book => `
            <div class="selected-book-item">
                ${book.coverUrl 
                    ? `<div class="cover-wrapper">
                         ${this.renderCoverImg(book, true)}
                         ${this.generatePlaceholderCover(book)}
                       </div>`
                    : `<div class="cover-wrapper">${this.generatePlaceholderCover(book)}</div>`
                }
                <div class="result-info">
                    <div class="result-title">${this.escapeHtml(book.title)}</div>
                    <div class="result-author">${this.escapeHtml(book.author)}</div>
                    ${book.snippet ? `<div class="result-snippet" style="cursor:pointer;" onclick="event.stopPropagation();app.showSelectedBookDescription('${book.key}')">${this.escapeHtml(book.snippet.substring(0, 80))}${book.snippet.length > 80 ? '...' : ''}</div>` : ''}
                </div>
                <button class="remove-book" onclick="app.removeBook('${book.key}')">×</button>
            </div>
        `).join('');
    }

    // 创建书单
    createList() {
        const listName = document.getElementById('listName').value.trim();
        
        if (!listName) {
            this.showToast('请输入书单名称');
            return;
        }

        if (this.selectedBooks.length < 3) {
            this.showToast('请至少添加3本书');
            return;
        }

        if (this.voteCount > this.selectedBooks.length) {
            this.showToast(`投票数量(${this.voteCount})不能超过书籍数量(${this.selectedBooks.length})`);
            return;
        }

        // 生成6位书单码
        const listCode = this.generateListCode();
        
        const newList = {
            id: Date.now().toString(),
            code: listCode,
            name: listName,
            creator: this.currentUser,
            voteCount: this.voteCount,
            books: [...this.selectedBooks],
            votes: [],
            createdAt: new Date().toISOString(),
            isPublic: true,
            isLocked: false
        };

        // 保存到 localStorage
        const allLists = this.getAllLists();
        allLists.push(newList);
        localStorage.setItem('booklist_all', JSON.stringify(allLists));

        this.showToast('书单创建成功！');
        
        // 显示二维码
        this.showQRCode(listCode);
        
        // 清空表单
        document.getElementById('listName').value = '';
        this.selectedBooks = [];
        this.renderSelectedBooks();
        document.getElementById('searchInput').value = '';
        this.searchResults = [];
        document.getElementById('searchResults').innerHTML = '';
    }

    // 生成书单码
    generateListCode() {
        const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
        let code = '';
        for (let i = 0; i < 6; i++) {
            code += chars.charAt(Math.floor(Math.random() * chars.length));
        }
        return code;
    }

    // 获取所有书单
    getAllLists() {
        const saved = localStorage.getItem('booklist_all');
        return saved ? JSON.parse(saved) : [];
    }

    // 保存所有书单
    saveAllLists(lists) {
        localStorage.setItem('booklist_all', JSON.stringify(lists));
    }

    // 显示二维码
    showQRCode(code) {
        const modal = document.getElementById('qrModal');
        const qrContainer = document.getElementById('qrcode');
        const codeSpan = document.getElementById('qrCode');
        
        qrContainer.innerHTML = '';
        codeSpan.textContent = code;

        try {
            // 生成二维码
            new QRCode(qrContainer, {
                text: 'BL:' + code,
                width: 200,
                height: 200,
                colorDark: '#2d3748',
                colorLight: '#ffffff',
                correctLevel: QRCode.CorrectLevel.M
            });
            modal.classList.remove('hidden');
        } catch (error) {
            console.error('二维码生成失败:', error);
            // 如果二维码生成失败，至少显示书单码
            qrContainer.innerHTML = '<p style="text-align:center;padding:20px;color:#718096;">二维码生成失败，请手动复制书单码</p>';
            modal.classList.remove('hidden');
        }
    }

    // 复制书单码
    copyListCode() {
        const code = document.getElementById('qrCode').textContent;
        navigator.clipboard.writeText(code).then(() => {
            this.showToast('已复制到剪贴板');
        }).catch(() => {
            this.showToast('复制失败，请手动复制');
        });
    }

    // 加载我的书单
    loadMyLists() {
        const container = document.getElementById('myLists');
        const allLists = this.getAllLists();
        const myLists = allLists.filter(l => l.creator === this.currentUser);

        if (myLists.length === 0) {
            container.innerHTML = '<p class="hint">还没有创建书单，快去创建一个吧！</p>';
            return;
        }

        container.innerHTML = myLists.map(list => {
            const isLocked = list.isLocked || list.votes.length > 0;
            return `
            <div class="my-list-item">
                <div class="my-list-header">
                    <div class="my-list-name">${this.escapeHtml(list.name)}</div>
                    <div class="my-list-actions">
                        <button class="btn" onclick="app.showQRCode('${list.code}')">分享</button>
                        ${!isLocked ? `<button class="btn btn-edit" onclick="app.editList('${list.id}')">编辑</button>` : ''}
                        <button class="btn" onclick="app.viewListResult('${list.id}')">结果</button>
                        <button class="btn btn-delete" onclick="app.deleteList('${list.id}')">删除</button>
                    </div>
                </div>
                <div class="my-list-info">
                    书单码: <strong>${list.code}</strong> |
                    ${list.books.length}本书 |
                    ${list.votes.length}人已投票
                    ${isLocked ? ' | <span class="locked-badge">已锁定</span>' : ' | <span class="unlocked-badge">可编辑</span>'}
                </div>
            </div>
            `;
        }).join('');
    }

    // 编辑书单
    editList(listId) {
        const allLists = this.getAllLists();
        const list = allLists.find(l => l.id === listId);
        if (!list) {
            this.showToast('书单不存在');
            return;
        }

        if (list.isLocked || list.votes.length > 0) {
            this.showToast('书单已有投票，无法编辑');
            return;
        }

        // 切换到创建书单标签，但预填书单数据
        this.switchTab('create');

        document.getElementById('listName').value = list.name;
        this.voteCount = list.voteCount;
        
        // 设置投票数量按钮
        document.querySelectorAll('.count-btn').forEach(btn => {
            btn.classList.toggle('active', parseInt(btn.dataset.count) === list.voteCount);
        });

        this.selectedBooks = [...list.books];
        this.renderSelectedBooks();

        // 保存当前编辑的书单ID
        this.editingListId = listId;

        // 修改创建按钮为保存按钮
        const createBtn = document.getElementById('createListBtn');
        createBtn.textContent = '保存修改';
        createBtn.onclick = () => this.finishEditList(listId);

        this.showToast('现在可以编辑书单，添加或删除书籍');
    }

    // 完成编辑书单
    finishEditList(listId) {
        const listName = document.getElementById('listName').value.trim();

        if (!listName) {
            this.showToast('请输入书单名称');
            return;
        }

        if (this.selectedBooks.length < 3) {
            this.showToast('请至少保留3本书');
            return;
        }

        if (this.voteCount > this.selectedBooks.length) {
            this.showToast(`投票数量(${this.voteCount})不能超过书籍数量(${this.selectedBooks.length})`);
            return;
        }

        const allLists = this.getAllLists();
        const listIndex = allLists.findIndex(l => l.id === listId);
        if (listIndex === -1) {
            this.showToast('书单不存在');
            return;
        }

        // 更新书单
        allLists[listIndex].name = listName;
        allLists[listIndex].voteCount = this.voteCount;
        allLists[listIndex].books = [...this.selectedBooks];
        
        this.saveAllLists(allLists);

        this.showToast('书单已更新！');

        // 重置编辑状态
        this.resetCreateForm();
        this.loadMyLists();
    }

    // 删除书单
    deleteList(listId) {
        const allLists = this.getAllLists();
        const list = allLists.find(l => l.id === listId);
        if (!list) {
            this.showToast('书单不存在');
            return;
        }

        if (!confirm(`确定要删除书单 "${list.name}" 吗？此操作不可恢复。`)) {
            return;
        }

        // 删除书单
        const updatedLists = allLists.filter(l => l.id !== listId);
        this.saveAllLists(updatedLists);

        this.showToast('书单已删除');
        this.loadMyLists();
    }

    // 重置创建表单
    resetCreateForm() {
        document.getElementById('listName').value = '';
        this.selectedBooks = [];
        this.renderSelectedBooks();
        document.getElementById('searchInput').value = '';
        this.searchResults = [];
        document.getElementById('searchResults').innerHTML = '';
        
        // 恢复创建按钮
        const createBtn = document.getElementById('createListBtn');
        createBtn.textContent = '创建书单';
        createBtn.onclick = () => this.createList();
        this.editingListId = null;
    }

    // 加载公开书单
    loadAvailableLists() {
        const container = document.getElementById('availableLists');
        const allLists = this.getAllLists();
        const availableLists = allLists.filter(l => l.isPublic);

        if (availableLists.length === 0) {
            container.innerHTML = '<p class="hint">暂无公开书单</p>';
            return;
        }

        container.innerHTML = availableLists.map(list => `
            <div class="list-item" onclick="app.startVote('${list.id}')">
                <div class="list-item-name">${this.escapeHtml(list.name)}</div>
                <div class="list-item-info">
                    创建者: ${this.escapeHtml(list.creator)} | 
                    书单码: ${list.code} |
                    ${list.books.length}本书
                </div>
            </div>
        `).join('');
    }

    // 通过书单码加入
    joinByCode() {
        const code = document.getElementById('listCodeInput').value.trim().toUpperCase();
        if (!code) {
            this.showToast('请输入书单码');
            return;
        }

        const allLists = this.getAllLists();
        const list = allLists.find(l => l.code === code);
        
        if (!list) {
            this.showToast('书单码不存在');
            return;
        }

        this.startVote(list.id);
    }

    // 开始投票
    startVote(listId) {
        const allLists = this.getAllLists();
        const list = allLists.find(l => l.id === listId);
        if (!list) return;

        // 检查是否已投票
        const alreadyVoted = list.votes.some(v => v.voter === this.currentUser);
        if (alreadyVoted) {
            if (!confirm('您已经投过票，是否重新投票？')) {
                return;
            }
            // 移除旧投票
            list.votes = list.votes.filter(v => v.voter !== this.currentUser);
        }

        this.currentVoteList = list;
        
        document.getElementById('listCodeInput').value = '';
        document.getElementById('voteListName').textContent = list.name;
        document.getElementById('voteRule').textContent = 
            `每人可投票选择 ${list.voteCount} 本书（共 ${list.books.length} 本候选）`;
        
        this.renderVoteBooks();
        document.getElementById('votePanel').classList.remove('hidden');
    }

    // 渲染投票书籍
    renderVoteBooks() {
        const container = document.getElementById('voteBooks');
        const list = this.currentVoteList;
        
        if (!list) return;

        container.innerHTML = list.books.map((book, index) => `
            <div class="vote-book-item" data-index="${index}" onclick="app.toggleVote(${index})">
                ${book.coverUrl 
                    ? `<div class="cover-wrapper">
                         ${this.renderCoverImg(book, true)}
                         ${this.generatePlaceholderCover(book)}
                       </div>`
                    : `<div class="cover-wrapper">${this.generatePlaceholderCover(book)}</div>`
                }
                <div class="result-info">
                    <div class="result-title">${this.escapeHtml(book.title)}</div>
                    <div class="result-author">${this.escapeHtml(book.author)}</div>
                    ${book.snippet ? `<div class="result-snippet" style="cursor:pointer;" onclick="event.stopPropagation();app.showVoteBookDescription(${index})">${this.escapeHtml(book.snippet.substring(0, 80))}${book.snippet.length > 80 ? '...' : ''}</div>` : ''}
                </div>
                <div class="checkbox">✓</div>
            </div>
        `).join('');

        this.selectedVoteBooks = [];
    }

    // 切换投票选择
    toggleVote(index) {
        const list = this.currentVoteList;
        if (!list) return;

        if (!this.selectedVoteBooks) this.selectedVoteBooks = [];

        const pos = this.selectedVoteBooks.indexOf(index);
        
        if (pos > -1) {
            this.selectedVoteBooks.splice(pos, 1);
        } else {
            if (this.selectedVoteBooks.length >= list.voteCount) {
                this.showToast(`最多只能选择 ${list.voteCount} 本`);
                return;
            }
            this.selectedVoteBooks.push(index);
        }

        // 更新UI
        document.querySelectorAll('.vote-book-item').forEach((item, i) => {
            item.classList.toggle('selected', this.selectedVoteBooks.includes(i));
        });
    }

    // 提交投票
    submitVote() {
        const list = this.currentVoteList;
        if (!list) return;

        if (!this.selectedVoteBooks || this.selectedVoteBooks.length === 0) {
            this.showToast('请至少选择一本书');
            return;
        }

        const vote = {
            voter: this.currentUser,
            bookIndices: [...this.selectedVoteBooks],
            timestamp: new Date().toISOString()
        };

        // 保存投票
        const allLists = this.getAllLists();
        const listIndex = allLists.findIndex(l => l.id === list.id);
        if (listIndex > -1) {
            allLists[listIndex].votes.push(vote);
            this.saveAllLists(allLists);
        }

        this.showToast('投票成功！');
        document.getElementById('votePanel').classList.add('hidden');
        this.selectedVoteBooks = [];
        this.currentVoteList = null;
    }

    // 加载结果列表
    loadResultLists() {
        const select = document.getElementById('resultListSelect');
        const allLists = this.getAllLists();
        const listsWithVotes = allLists.filter(l => l.votes.length > 0);

        if (listsWithVotes.length === 0) {
            select.innerHTML = '<option value="">暂无投票数据</option>';
            return;
        }

        select.innerHTML = '<option value="">请选择书单</option>' + 
            listsWithVotes.map(l => `<option value="${l.id}">${this.escapeHtml(l.name)} (${l.votes.length}票)</option>`).join('');
    }

    // 查看某个列表的结果
    viewListResult(listId) {
        this.switchTab('result');
        setTimeout(() => {
            document.getElementById('resultListSelect').value = listId;
            this.showResult(listId);
        }, 100);
    }

    // 显示投票结果
    showResult(listId) {
        const allLists = this.getAllLists();
        const list = allLists.find(l => l.id === listId);
        const container = document.getElementById('resultContent');

        if (!list || list.votes.length === 0) {
            container.innerHTML = '<p class="hint">暂无投票数据</p>';
            return;
        }

        // 统计每本书的得票数
        const voteCounts = new Array(list.books.length).fill(0);
        list.votes.forEach(vote => {
            vote.bookIndices.forEach(index => {
                if (index < voteCounts.length) {
                    voteCounts[index]++;
                }
            });
        });

        // 找出最高得票
        const maxVotes = Math.max(...voteCounts);
        const winners = voteCounts
            .map((count, index) => ({ count, index }))
            .filter(item => item.count === maxVotes && item.count > 0);

        const isTie = winners.length > 1;

        // 按得票数排序书籍
        const sortedBooks = list.books
            .map((book, index) => ({ ...book, index, votes: voteCounts[index] }))
            .sort((a, b) => b.votes - a.votes);

        container.innerHTML = `
            <div style="margin-bottom:20px;padding:12px;background:#f7fafc;border-radius:8px;">
                <strong>总投票数:</strong> ${list.votes.length} 票 | 
                <strong>候选书籍:</strong> ${list.books.length} 本
            </div>
        ` + sortedBooks.map(book => {
            const isWinner = book.votes === maxVotes && book.votes > 0;
            const zlibraryUrl = `https://www.z-library.is/s/${encodeURIComponent(book.title)}`;
            
            return `
                <div class="result-book-item ${isWinner ? (isTie ? 'tie' : 'winner') : ''}">
                    ${book.coverUrl 
                        ? `<div class="cover-wrapper">
                             ${this.renderCoverImg(book, true)}
                             ${this.generatePlaceholderCover(book)}
                           </div>`
                        : `<div class="cover-wrapper">${this.generatePlaceholderCover(book)}</div>`
                    }
                    <div class="result-book-info">
                        <div class="result-title">${this.escapeHtml(book.title)}</div>
                        <div class="result-author">${this.escapeHtml(book.author)}</div>
                        ${isWinner ? `<a href="${zlibraryUrl}" target="_blank" class="zlibrary-link" onclick="app.copyAndOpenZLib('${this.escapeHtml(book.title)}', '${zlibraryUrl}')">🔍 Z-Library</a>` : ''}
                    </div>
                    <div class="vote-count">${book.votes}票</div>
                    ${isWinner ? `<span class="${isTie ? 'tie-badge' : 'winner-badge'}">${isTie ? '平票' : '获胜'}</span>` : ''}
                </div>
            `;
        }).join('');
    }

    generatePlaceholderCover(book) {
        const colorIndex = (book.key.charCodeAt(book.key.length - 1)) % this.coverColors.length;
        const bgColor = this.coverColors[colorIndex];
        const title = this.escapeHtml(book.title);
        const canvasId = 'canvas_' + book.key.replace(/[^a-zA-Z0-9]/g, '_');
        
        return `<div class="book-cover-placeholder" style="background: linear-gradient(135deg, ${bgColor}, ${this.coverColors[(colorIndex + 5) % this.coverColors.length]});" title="${title}">
        <span class="cover-title">${title.substring(0, 4)}</span>
    </div>`;
    }

    // 复制书名并打开 Z-Library
    copyAndOpenZLib(title, url) {
        // 复制书名到剪贴板
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(title).then(() => {
                this.showToast(`已复制书名"${title}"，请在Z-Library粘贴搜索`);
            }).catch(() => {
                this.fallbackCopy(title);
            });
        } else {
            this.fallbackCopy(title);
        }
        // 延迟打开链接，让用户看到提示
        setTimeout(() => {
            window.open(url, '_blank');
        }, 300);
    }

    // 备用复制方法
    fallbackCopy(text) {
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        try {
            document.execCommand('copy');
            this.showToast(`已复制书名"${text}"，请在Z-Library粘贴搜索`);
        } catch (e) {
            this.showToast('复制失败，请手动复制书名');
        }
        document.body.removeChild(textarea);
    }

    // HTML 转义
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // 带超时的 fetch
    fetchWithTimeout(url, options = {}, timeout = 5000) {
        return Promise.race([
            fetch(url, options),
            new Promise((_, reject) => 
                setTimeout(() => reject(new Error('请求超时')), timeout)
            )
        ]);
    }

    // 封面代理URL
    proxyCoverUrl(url) {
        if (!url) return '';
        return `${this.backendApiUrl}/api/cover?url=${encodeURIComponent(url)}`;
    }

    // 放大封面
    enlargeCover(url) {
        if (!url) return;
        document.getElementById('coverModalImg').src = url;
        document.getElementById('coverModal').classList.remove('hidden');
    }

    // 显示简介全文
    showFullDescription(title, text) {
        document.getElementById('descriptionModalTitle').textContent = title;
        document.getElementById('descriptionModalText').textContent = text || '暂无简介';
        document.getElementById('descriptionModal').classList.remove('hidden');
    }

    // 显示投票书籍简介
    showVoteBookDescription(index) {
        const book = this.currentVoteList.books[index];
        if (book) {
            this.showFullDescription(book.title, book.snippet || book.description || '暂无简介');
        }
    }

    // 显示已选书籍简介
    showSelectedBookDescription(key) {
        const book = this.selectedBooks.find(b => b.key === key);
        if (book) {
            this.showFullDescription(book.title, book.snippet || '暂无简介');
        }
    }

    // 生成封面img标签 (统一处理代理重试)
    renderCoverImg(book, enlargeable = false) {
        if (!book.coverUrl) return '';
        const onerrorRetry = `if(!this.dataset.proxied){this.dataset.proxied='1';this.src='${this.backendApiUrl}/api/cover?url='+encodeURIComponent(this.dataset.orig);}else{var p=this.nextElementSibling;if(p)p.style.display='flex';this.remove();}`;
        const clickHandler = enlargeable ? ` onclick="event.stopPropagation();app.enlargeCover(this.src)"` : '';
        return `<img src="${book.coverUrl}" data-orig="${book.coverUrl}" alt="${book.title}" class="result-cover" style="display:none;cursor:pointer;"${clickHandler} onload="this.style.display='block';this.nextElementSibling.style.display='none';" onerror="${onerrorRetry}">`;
    }

    // 显示 Toast
    showToast(message) {
        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.textContent = message;
        document.body.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 300);
        }, 2000);
    }
}

// 启动应用
const app = new BookListApp();
