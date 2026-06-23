/**
 * 预测交互逻辑
 */

let predictHistory = [];
let gaugeChart = null;

// ==================== 实时预测 ====================

async function doPredict() {
    const text = document.getElementById('predictInput').value.trim();
    if (!text) {
        alert('请输入金融新闻标题');
        return;
    }

    try {
        const res = await fetch('/api/predict', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text })
        });

        if (!res.ok) throw new Error('请求失败');

        const result = await res.json();
        displayResult(result);
        addToHistory(result);
    } catch (e) {
        alert('预测失败: ' + e.message);
    }
}

function displayResult(result) {
    document.getElementById('resultCard').style.display = 'block';

    // 仪表盘
    const probPos = result.prob_positive || result.confidence || 0.5;
    if (result.sentiment === 'negative') {
        renderGauge(1 - probPos);
    } else {
        renderGauge(probPos);
    }

    // 文字结果
    const sentimentEl = document.getElementById('resultSentiment');
    sentimentEl.textContent = result.sentiment_zh;
    sentimentEl.className = 'mt-2 ' + (result.sentiment === 'positive' ? 'text-success' : 'text-danger');

    // 信号
    const signalEl = document.getElementById('resultSignal');
    signalEl.textContent = result.signal_zh || '';
    signalEl.className = 'fs-5 ' + getSignalClass(result.signal);

    // 进度条
    const negPct = Math.round((result.prob_negative || (1 - probPos)) * 100);
    const posPct = Math.round((result.prob_positive || probPos) * 100);

    const barNeg = document.getElementById('resultBarNegative');
    const barPos = document.getElementById('resultBarPositive');

    barNeg.style.width = negPct + '%';
    barNeg.textContent = '消极 ' + negPct + '%';
    barPos.style.width = posPct + '%';
    barPos.textContent = '积极 ' + posPct + '%';

    // 标签
    document.getElementById('resultConfidence').textContent =
        '置信度: ' + (result.confidence * 100).toFixed(1) + '%';
    document.getElementById('resultLabel').textContent =
        result.sentiment === 'positive' ? '利好' : '利空';
    document.getElementById('resultLabel').className =
        'badge ' + (result.sentiment === 'positive' ? 'bg-success' : 'bg-danger');

    // 滚动到结果
    document.getElementById('resultCard').scrollIntoView({ behavior: 'smooth' });
}

function renderGauge(value) {
    const chartDom = document.getElementById('gaugeChart');
    if (gaugeChart) gaugeChart.dispose();

    gaugeChart = echarts.init(chartDom);

    const option = {
        series: [{
            type: 'gauge',
            startAngle: 180,
            endAngle: 0,
            min: 0,
            max: 1,
            splitNumber: 5,
            axisLine: {
                lineStyle: {
                    width: 20,
                    color: [
                        [0.3, '#ef4444'],
                        [0.5, '#f59e0b'],
                        [0.7, '#3b82f6'],
                        [1, '#10b981']
                    ]
                }
            },
            pointer: {
                icon: 'path://M12.8,0.7l12,40.1H0.7L12.8,0.7z',
                length: '70%',
                width: 8,
                offsetCenter: [0, '-10%'],
                itemStyle: {
                    color: 'auto'
                }
            },
            axisTick: {
                length: 10,
                lineStyle: { color: 'auto', width: 1 }
            },
            splitLine: {
                length: 25,
                lineStyle: { color: 'auto', width: 3 }
            },
            axisLabel: {
                color: '#94a3b8',
                fontSize: 12,
                distance: -40,
                formatter: function (v) {
                    return (v * 100).toFixed(0) + '%';
                }
            },
            title: {
                offsetCenter: [0, '-20%'],
                fontSize: 14,
                color: '#94a3b8'
            },
            detail: {
                fontSize: 28,
                offsetCenter: [0, '40%'],
                valueAnimation: true,
                formatter: function (v) {
                    return (v * 100).toFixed(1) + '%';
                },
                color: '#1a202c'
            },
            data: [{ value: value, name: '积极概率' }]
        }]
    };

    gaugeChart.setOption(option);

    // 响应式
    window.addEventListener('resize', () => gaugeChart?.resize());
}

function getSignalClass(signal) {
    const map = {
        'strong_buy': 'text-success pulse-green',
        'buy': 'text-success',
        'strong_sell': 'text-danger pulse-red',
        'sell': 'text-danger',
        'neutral': 'text-muted'
    };
    return map[signal] || '';
}

// ==================== 预测历史 ====================

function addToHistory(result) {
    predictHistory.unshift({
        ...result,
        time: new Date().toLocaleString('zh-CN')
    });

    if (predictHistory.length > 20) predictHistory.pop();
    renderHistory();
}

function renderHistory() {
    const container = document.getElementById('predictHistory');
    if (predictHistory.length === 0) {
        container.innerHTML = '<p class="text-muted text-center">暂无预测记录</p>';
        return;
    }

    container.innerHTML = predictHistory.map((h, i) => `
        <div class="news-item ${h.sentiment}">
            <div class="d-flex justify-content-between align-items-start">
                <div class="flex-grow-1 me-2">
                    <small class="text-truncate d-block" style="max-width:350px;">${h.text}</small>
                    <small class="text-muted">${h.time}</small>
                </div>
                <div class="text-end">
                    <span class="tag tag-${h.sentiment}">${h.sentiment_zh}</span>
                    <br/><small class="text-muted">${(h.confidence * 100).toFixed(1)}%</small>
                </div>
            </div>
        </div>
    `).join('');
}

function clearHistory() {
    predictHistory = [];
    renderHistory();
}

function clearPredict() {
    document.getElementById('predictInput').value = '';
    document.getElementById('resultCard').style.display = 'none';
}

function setExample(text) {
    document.getElementById('predictInput').value = text;
    document.querySelectorAll('#mainTabs button[data-bs-toggle="tab"]').forEach(t => {
        t.classList.remove('active');
    });
    document.querySelector('[data-bs-target="#tab-predict"]').classList.add('active');
    document.getElementById('tab-predict').classList.add('show', 'active');
}

// ==================== 批量预测 ====================

async function doBatchPredict() {
    const raw = document.getElementById('batchInput').value.trim();
    if (!raw) return;

    const texts = raw.split('\n').filter(t => t.trim());
    if (texts.length === 0) return;

    try {
        const res = await fetch('/api/predict_batch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ texts })
        });

        const data = await res.json();

        document.getElementById('batchResults').innerHTML = `
            <div class="alert alert-info">
                共分析 <strong>${data.total}</strong> 条 |
                积极: <strong class="text-success">${data.summary.positive}</strong> |
                消极: <strong class="text-danger">${data.summary.negative}</strong>
            </div>
            <div class="table-responsive" style="max-height:400px;overflow-y:auto;">
                <table class="table table-sm">
                    <thead><tr><th>文本</th><th>情感</th><th>置信度</th><th>信号</th></tr></thead>
                    <tbody>
                        ${data.results.map(r => `
                            <tr>
                                <td class="text-truncate" style="max-width:250px;">${r.text}</td>
                                <td><span class="tag tag-${r.sentiment}">${r.sentiment_zh}</span></td>
                                <td>${(r.confidence * 100).toFixed(1)}%</td>
                                <td>${r.signal_zh || ''}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
    } catch (e) {
        alert('批量预测失败: ' + e.message);
    }
}

// ==================== 实时新闻 ====================

// ==================== 样例新闻 & 热点新闻 ====================

async function fetchSampleNews() {
    await loadNewsTab('sample');
}

async function fetchRealNews() {
    await loadNewsTab('realtime');
}

async function loadNewsTab(mode) {
    const isRealtime = mode === 'realtime';
    const prefix = isRealtime ? 'real' : 'sample';

    // Loading state
    const listEl = document.getElementById(prefix + 'NewsList');
    if (listEl) listEl.innerHTML = '<div class="loading-spinner"><div class="spinner"></div><p class="mt-2">加载中...</p></div>';

    try {
        const endpoint = isRealtime ? '/api/news/realtime' : '/api/news/sample';
        const res = await fetch(`${endpoint}?limit=30`);
        const data = await res.json();

        // 更新时间
        const timeEl = document.getElementById(prefix + 'FetchTime');
        if (timeEl) timeEl.textContent = '获取时间: ' + data.fetch_time;

        // 信号
        const iconEl = document.getElementById(prefix + 'SignalIcon');
        const textEl = document.getElementById(prefix + 'SignalText');
        if (iconEl && textEl) {
            if (data.market_signal_en === 'bullish') {
                iconEl.textContent = '🔴'; iconEl.className = 'pulse-red';
            } else if (data.market_signal_en === 'bearish') {
                iconEl.textContent = '🟢'; iconEl.className = 'pulse-green';
            } else {
                iconEl.textContent = '⚪'; iconEl.className = '';
            }
            textEl.textContent = data.market_signal;
        }

        // 统计 (红正绿负)
        const posEl = document.getElementById(prefix + 'PosCount');
        const negEl = document.getElementById(prefix + 'NegCount');
        if (posEl) posEl.textContent = data.positive_count;
        if (negEl) negEl.textContent = data.negative_count;

        // 新闻总数
        const totalEl = document.getElementById(prefix + 'TotalBadge');
        if (totalEl) totalEl.textContent = data.total;

        // 新闻列表
        renderNewsListTo(prefix + 'NewsList', data.news);

        // 情绪趋势图
        renderSentimentTrendTo(prefix + 'TrendChart', data.news);

        // 板块情绪图
        if (data.sectors && data.sectors.length > 0) {
            renderSectorChartTo(prefix + 'SectorChart', data.sectors);
        }

    } catch (e) {
        if (listEl) listEl.innerHTML = '<p class="text-danger text-center">获取失败: ' + e.message + '</p>';
    }
}

function renderSectorChartTo(domId, sectors) {
    const chartDom = document.getElementById(domId);
    if (!chartDom) return;
    const chart = echarts.init(chartDom);

    const names = sectors.map(d => d.sector);
    const scores = sectors.map(d => d.sentiment_score);

    chart.setOption({
        tooltip: { trigger: 'axis' },
        grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
        xAxis: {
            type: 'category', data: names,
            axisLabel: { rotate: 45, color: '#5a6b7c', fontSize: 12 }
        },
        yAxis: {
            type: 'value', name: '情绪得分',
            axisLabel: { color: '#5a6b7c' },
            splitLine: { lineStyle: { color: '#e2e8f0' } }
        },
        series: [{
            type: 'bar',
            data: scores.map(v => ({
                value: v,
                itemStyle: { color: v > 0.2 ? '#ef4444' : v < -0.2 ? '#10b981' : '#f59e0b' }
            })),
            barWidth: '60%'
        }]
    });
    window.addEventListener('resize', () => chart.resize());
}

function renderNewsListTo(domId, news) {
    const container = document.getElementById(domId);
    if (!container) return;
    container.innerHTML = news.map(n => `
        <div class="news-item ${n.sentiment}">
            <div class="d-flex justify-content-between align-items-start">
                <div class="flex-grow-1">
                    <span class="tag tag-${n.sentiment} me-2">${n.sentiment_zh}</span>
                    <span>${n.title}</span>
                </div>
                <div class="text-end ms-2" style="min-width:110px;">
                    <small class="text-muted">${n.time || ''}</small><br/>
                    <small class="text-muted">${n.source || ''}</small>
                    <span class="badge ms-1 ${n.sentiment === 'positive' ? 'bg-danger' : n.sentiment === 'negative' ? 'bg-success' : 'bg-secondary'}">
                        ${(n.confidence * 100).toFixed(0)}%
                    </span>
                </div>
            </div>
        </div>
    `).join('');
}

function renderSentimentTrendTo(domId, news) {
    const chartDom = document.getElementById(domId);
    if (!chartDom) return;
    const chart = echarts.init(chartDom);

    const sorted = [...news].reverse();
    let cumPos = 0, cumNeg = 0;
    const times = [], posData = [], negData = [], netData = [];

    sorted.forEach((n, i) => {
        if (n.sentiment === 'positive') cumPos++;
        else if (n.sentiment === 'negative') cumNeg++;
        times.push(i + 1);
        posData.push(cumPos);
        negData.push(cumNeg);
        netData.push(cumPos - cumNeg);
    });

    chart.setOption({
        tooltip: { trigger: 'axis' },
        legend: {
            data: ['累计积极', '累计消极', '净情绪'],
            textStyle: { color: '#5a6b7c' }
        },
        grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
        xAxis: { type: 'category', data: times, name: '新闻序号', axisLabel: { color: '#5a6b7c' } },
        yAxis: { type: 'value', axisLabel: { color: '#5a6b7c' }, splitLine: { lineStyle: { color: '#e2e8f0' } } },
        series: [
            { name: '累计积极', type: 'line', data: posData, lineStyle: { color: '#ef4444', width: 2 }, areaStyle: { color: 'rgba(239,68,68,0.15)' } },
            { name: '累计消极', type: 'line', data: negData, lineStyle: { color: '#10b981', width: 2 }, areaStyle: { color: 'rgba(16,185,129,0.15)' } },
            { name: '净情绪', type: 'line', data: netData, lineStyle: { color: '#3b82f6', width: 2, type: 'dashed' } }
        ]
    });
    window.addEventListener('resize', () => chart.resize());
}

// ==================== 文件上传 ====================

function handleFileSelect() {
    const file = document.getElementById('fileInput').files[0];
    if (file) {
        document.getElementById('fileNameDisplay').textContent = '已选择: ' + file.name;
    }
}

function handleFileDrop(event) {
    event.preventDefault();
    const file = event.dataTransfer.files[0];
    document.getElementById('fileInput').files = event.dataTransfer.files;
    handleFileSelect();
}

async function uploadAndAnalyze() {
    const fileInput = document.getElementById('fileInput');
    if (!fileInput.files.length) {
        alert('请先选择文件');
        return;
    }

    document.getElementById('uploadProgress').style.display = 'block';

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);

    try {
        const res = await fetch('/api/upload_analyze', {
            method: 'POST',
            body: formData
        });

        const data = await res.json();
        document.getElementById('uploadProgress').style.display = 'none';

        if (data.error) {
            alert('分析失败: ' + data.error);
            return;
        }

        document.getElementById('uploadResults').innerHTML = `
            <div class="alert alert-success">
                <h5>✅ 分析完成</h5>
                <p>总样本: ${data.total} | 积极: ${data.positive} | 消极: ${data.negative}</p>
                <a href="${data.download_url}" class="btn btn-sm btn-primary" download>
                    <i class="bi bi-download"></i> 下载分析结果
                </a>
            </div>
            <div class="table-responsive" style="max-height:300px;overflow-y:auto;">
                <table class="table table-sm">
                    <thead><tr><th>文本</th><th>情感</th><th>置信度</th><th>信号</th></tr></thead>
                    <tbody>
                        ${(data.preview || []).map(r => `
                            <tr>
                                <td class="text-truncate" style="max-width:200px;">${r.text}</td>
                                <td><span class="tag tag-${r.sentiment}">${r.sentiment_zh}</span></td>
                                <td>${(r.confidence * 100).toFixed(1)}%</td>
                                <td>${r.signal_zh || ''}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
    } catch (e) {
        document.getElementById('uploadProgress').style.display = 'none';
        alert('上传分析失败: ' + e.message);
    }
}
