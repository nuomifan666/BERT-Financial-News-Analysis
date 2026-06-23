/**
 * 看板图表渲染逻辑
 */

// 存储图表实例用于响应式缩放
const chartInstances = {};

function getOrCreateChart(domId) {
    if (chartInstances[domId]) {
        chartInstances[domId].dispose();
    }
    const dom = document.getElementById(domId);
    if (!dom) return null;
    const chart = echarts.init(dom);
    chartInstances[domId] = chart;
    return chart;
}

// ==================== 看板数据加载 ====================

async function loadDashboardData() {
    try {
        const res = await fetch('/api/data/statistics');
        const data = await res.json();

        // 统计卡片
        document.getElementById('statTotal').textContent = data.total || '-';
        document.getElementById('statPositive').textContent = data.positive || '-';
        document.getElementById('statNegative').textContent = data.negative || '-';
        document.getElementById('statAvgLen').textContent = data.avg_length || '-';

        // 饼图
        renderLabelPie(data.positive || 0, data.negative || 0);

        // 长度分布柱状图
        if (data.length_distribution) {
            renderLengthBar(data.length_distribution);
        }
    } catch (e) {
        console.error('看板数据加载失败:', e);
    }
}

function renderLabelPie(positive, negative) {
    const chart = getOrCreateChart('labelPieChart');
    if (!chart) return;

    const option = {
        tooltip: {
            trigger: 'item',
            formatter: '{b}: {c} ({d}%)'
        },
        legend: {
            orient: 'vertical',
            left: 'left',
            textStyle: { color: '#5a6b7c' }
        },
        series: [{
            name: '标签分布',
            type: 'pie',
            radius: ['50%', '75%'],
            center: ['55%', '55%'],
            avoidLabelOverlap: false,
            itemStyle: {
                borderRadius: 8,
                borderColor: '#ffffff',
                borderWidth: 3
            },
            label: {
                show: true,
                formatter: '{b}\n{d}%',
                color: '#1a202c'
            },
            emphasis: {
                label: { fontSize: 16, fontWeight: 'bold' }
            },
            data: [
                {
                    value: positive,
                    name: '积极',
                    itemStyle: { color: '#10b981' }
                },
                {
                    value: negative,
                    name: '消极',
                    itemStyle: { color: '#ef4444' }
                }
            ]
        }]
    };

    chart.setOption(option);
}

function renderLengthBar(dist) {
    const chart = getOrCreateChart('lengthBarChart');
    if (!chart) return;

    const option = {
        tooltip: { trigger: 'axis' },
        grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
        xAxis: {
            type: 'category',
            data: dist.labels || [],
            axisLabel: { color: '#5a6b7c', rotate: 30 },
            name: '文本长度区间'
        },
        yAxis: {
            type: 'value',
            name: '数量',
            axisLabel: { color: '#5a6b7c' },
            splitLine: { lineStyle: { color: '#e2e8f0' } }
        },
        series: [{
            type: 'bar',
            data: (dist.values || []).map((v, i) => ({
                value: v,
                itemStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: '#3b82f6' },
                        { offset: 1, color: '#1d4ed8' }
                    ])
                }
            })),
            barWidth: '60%',
            itemStyle: {
                borderRadius: [6, 6, 0, 0]
            }
        }]
    };

    chart.setOption(option);
}

// ==================== 词云 ====================

async function loadWordClouds() {
    try {
        const res = await fetch('/api/visualization/wordcloud');
        const data = await res.json();

        renderSingleWordCloud('positiveWordCloud', data.positive || [], '#10b981');
        renderSingleWordCloud('negativeWordCloud', data.negative || [], '#ef4444');
    } catch (e) {
        console.error('词云加载失败:', e);
    }
}

function renderSingleWordCloud(domId, words, color) {
    const chart = getOrCreateChart(domId);
    if (!chart) return;

    if (!words || words.length === 0) {
        chart.setOption({
            title: { text: '暂无数据', left: 'center', top: 'center', textStyle: { color: '#5a6b7c' } }
        });
        return;
    }

    const maxVal = words[0]?.value || 1;

    const option = {
        tooltip: {
            show: true,
            formatter: '{b}: {c}'
        },
        series: [{
            type: 'wordCloud',
            shape: 'circle',
            left: 'center',
            top: 'center',
            width: '90%',
            height: '90%',
            sizeRange: [14, 50],
            rotationRange: [-45, 45],
            rotationStep: 15,
            gridSize: 8,
            drawOutOfBound: false,
            layoutAnimation: true,
            textStyle: {
                fontFamily: 'Microsoft YaHei, sans-serif',
                fontWeight: 'bold',
                color: function () {
                    const colors = [
                        color,
                        echarts.color.lift(color, 0.2),
                        echarts.color.lift(color, -0.1),
                    ];
                    return colors[Math.floor(Math.random() * colors.length)];
                }
            },
            emphasis: {
                textStyle: {
                    fontSize: 50,
                    color: '#1a202c'
                }
            },
            data: words.slice(0, 80)
        }]
    };

    chart.setOption(option);
}

// ==================== 训练历程图表 ====================

async function loadTrainingCharts() {
    try {
        const res = await fetch('/api/visualization/training_history');
        const data = await res.json();

        if (data.iterations && data.iterations.length > 0) {
            renderAccuracyF1Chart(data);
            renderPRChart(data);
        }

        // 混淆矩阵
        const cmRes = await fetch('/api/visualization/confusion_matrix');
        const cmData = await cmRes.json();
        renderConfusionMatrix(cmData);

        // ROC曲线
        const rocRes = await fetch('/api/visualization/roc');
        const rocData = await rocRes.json();
        renderROC(rocData);

        // 置信度分布
        const confRes = await fetch('/api/visualization/confidence');
        const confData = await confRes.json();
        renderConfidenceDist(confData);

    } catch (e) {
        console.error('训练图表加载失败:', e);
    }
}

function renderAccuracyF1Chart(data) {
    const chart = getOrCreateChart('accuracyChart');
    if (!chart) return;

    const option = {
        tooltip: { trigger: 'axis' },
        legend: {
            data: ['Accuracy', 'Weighted F1', 'Macro F1'],
            textStyle: { color: '#5a6b7c' }
        },
        grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
        xAxis: {
            type: 'category',
            data: data.iterations.map(i => '#' + i),
            axisLabel: { color: '#5a6b7c' }
        },
        yAxis: {
            type: 'value',
            min: 0,
            max: 1,
            axisLabel: {
                color: '#5a6b7c',
                formatter: v => (v * 100).toFixed(0) + '%'
            },
            splitLine: { lineStyle: { color: '#e2e8f0' } }
        },
        series: [
            {
                name: 'Accuracy', type: 'line', data: data.accuracy,
                lineStyle: { color: '#3b82f6', width: 2 },
                itemStyle: { color: '#3b82f6' },
                symbol: 'circle', symbolSize: 6
            },
            {
                name: 'Weighted F1', type: 'line', data: data.weighted_f1,
                lineStyle: { color: '#10b981', width: 2 },
                itemStyle: { color: '#10b981' },
                symbol: 'diamond', symbolSize: 6
            },
            {
                name: 'Macro F1', type: 'line', data: data.macro_f1,
                lineStyle: { color: '#f59e0b', width: 2, type: 'dashed' },
                itemStyle: { color: '#f59e0b' },
                symbol: 'triangle', symbolSize: 6
            }
        ]
    };

    chart.setOption(option);
}

function renderPRChart(data) {
    const chart = getOrCreateChart('prChart');
    if (!chart) return;

    const option = {
        tooltip: { trigger: 'axis' },
        legend: {
            data: ['Macro Precision', 'Macro Recall', 'Weighted Precision', 'Weighted Recall'],
            textStyle: { color: '#5a6b7c' },
            top: 0,
            type: 'scroll'
        },
        grid: { left: '3%', right: '4%', bottom: '3%', top: '15%', containLabel: true },
        xAxis: {
            type: 'category',
            data: data.iterations.map(i => '#' + i),
            axisLabel: { color: '#5a6b7c' }
        },
        yAxis: {
            type: 'value',
            min: 0,
            max: 1,
            axisLabel: {
                color: '#5a6b7c',
                formatter: v => (v * 100).toFixed(0) + '%'
            },
            splitLine: { lineStyle: { color: '#e2e8f0' } }
        },
        series: [
            {
                name: 'Macro Precision', type: 'line', data: data.macro_precision,
                lineStyle: { color: '#8b5cf6', width: 1.5 },
                symbol: 'circle', symbolSize: 5
            },
            {
                name: 'Macro Recall', type: 'line', data: data.macro_recall,
                lineStyle: { color: '#06b6d4', width: 1.5 },
                symbol: 'diamond', symbolSize: 5
            },
            {
                name: 'Weighted Precision', type: 'line', data: data.weighted_precision,
                lineStyle: { color: '#ec4899', width: 1.5 },
                symbol: 'triangle', symbolSize: 5
            },
            {
                name: 'Weighted Recall', type: 'line', data: data.weighted_recall,
                lineStyle: { color: '#14b8a6', width: 1.5 },
                symbol: 'square', symbolSize: 5
            }
        ]
    };

    chart.setOption(option);
}

function renderConfusionMatrix(data) {
    const chart = getOrCreateChart('confusionMatrixChart');
    if (!chart) return;

    const matrix = data.matrix || [[0, 0], [0, 0]];
    const labels = data.labels || ['消极', '积极'];

    // 转换为 heatmap 需要的格式
    const heatData = [];
    matrix.forEach((row, i) => {
        row.forEach((val, j) => {
            heatData.push([j, i, val]);
        });
    });

    const maxVal = Math.max(...heatData.map(d => d[2]), 1);

    const option = {
        tooltip: {
            position: 'top',
            formatter: params => {
                const v = params.data[2];
                const total = matrix.reduce((a, r) => a + r.reduce((b, c) => b + c, 0), 0);
                return `${labels[params.data[0]]} → ${labels[params.data[1]]}<br/>
                        数量: <b>${v}</b><br/>
                        占比: <b>${(v / total * 100).toFixed(1)}%</b>`;
            }
        },
        grid: { left: '5%', right: '5%', top: '5%', bottom: '5%' },
        xAxis: {
            type: 'category',
            data: labels,
            name: '预测标签',
            position: 'bottom',
            axisLabel: { color: '#1a202c', fontSize: 14 },
            splitArea: { show: true },
            axisLine: { lineStyle: { color: '#dde4ea' } }
        },
        yAxis: {
            type: 'category',
            data: labels,
            name: '真实标签',
            position: 'left',
            axisLabel: { color: '#1a202c', fontSize: 14 },
            splitArea: { show: true },
            axisLine: { lineStyle: { color: '#dde4ea' } }
        },
        visualMap: {
            min: 0,
            max: maxVal,
            calculable: true,
            orient: 'horizontal',
            left: 'center',
            bottom: '0%',
            inRange: {
                color: ['#e0f2fe', '#7dd3fc', '#38bdf8', '#0ea5e9', '#0284c7']
            },
            textStyle: { color: '#5a6b7c' }
        },
        series: [{
            type: 'heatmap',
            data: heatData,
            label: {
                show: true,
                color: '#1a202c',
                fontSize: 16,
                fontWeight: 'bold'
            },
            emphasis: {
                itemStyle: {
                    shadowBlur: 10,
                    shadowColor: 'rgba(0, 0, 0, 0.5)'
                }
            }
        }]
    };

    chart.setOption(option);
}

function renderROC(data) {
    const chart = getOrCreateChart('rocChart');
    if (!chart) return;

    const option = {
        tooltip: { trigger: 'axis' },
        grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
        xAxis: {
            type: 'value',
            name: 'False Positive Rate',
            min: 0, max: 1,
            axisLabel: { color: '#5a6b7c' },
            splitLine: { lineStyle: { color: '#e2e8f0' } }
        },
        yAxis: {
            type: 'value',
            name: 'True Positive Rate',
            min: 0, max: 1,
            axisLabel: { color: '#5a6b7c' },
            splitLine: { lineStyle: { color: '#e2e8f0' } }
        },
        series: [
            {
                name: `ROC (AUC = ${data.auc || 0})`,
                type: 'line',
                data: (data.fpr || []).map((x, i) => [x, (data.tpr || [])[i]]),
                smooth: true,
                lineStyle: { color: '#3b82f6', width: 3 },
                areaStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: 'rgba(59, 130, 246, 0.4)' },
                        { offset: 1, color: 'rgba(59, 130, 246, 0.05)' }
                    ])
                }
            },
            {
                name: '随机分类器',
                type: 'line',
                data: [[0, 0], [1, 1]],
                lineStyle: { color: '#ef4444', width: 1, type: 'dashed' },
                symbol: 'none'
            }
        ]
    };

    chart.setOption(option);
}

function renderConfidenceDist(data) {
    const chart = getOrCreateChart('confidenceChart');
    if (!chart) return;

    const bins = data.bins || [];
    const option = {
        tooltip: { trigger: 'axis' },
        legend: {
            data: ['正确-正面', '正确-负面', '错误-正面', '错误-负面'],
            textStyle: { color: '#5a6b7c' },
            type: 'scroll'
        },
        grid: { left: '3%', right: '4%', bottom: '3%', top: '15%', containLabel: true },
        xAxis: {
            type: 'category',
            data: bins.map(b => b.toFixed(1)),
            name: '置信度区间',
            axisLabel: { color: '#5a6b7c' }
        },
        yAxis: {
            type: 'value',
            name: '数量',
            axisLabel: { color: '#5a6b7c' },
            splitLine: { lineStyle: { color: '#e2e8f0' } }
        },
        series: [
            {
                name: '正确-正面', type: 'bar', data: data.correct_pos || [],
                stack: 'correct', itemStyle: { color: '#10b981' }, barWidth: '80%'
            },
            {
                name: '正确-负面', type: 'bar', data: data.correct_neg || [],
                stack: 'correct', itemStyle: { color: '#34d399' }
            },
            {
                name: '错误-正面', type: 'bar', data: data.wrong_pos || [],
                stack: 'wrong', itemStyle: { color: '#f87171' }
            },
            {
                name: '错误-负面', type: 'bar', data: data.wrong_neg || [],
                stack: 'wrong', itemStyle: { color: '#ef4444' }
            }
        ]
    };

    chart.setOption(option);
}

// ==================== 数据集浏览 ====================

let currentDataPage = 1;
let totalDataPages = 1;
let allSamplesCache = [];

async function loadDatasetPage(page) {
    try {
        // 获取数据统计
        const statsRes = await fetch('/api/data/statistics');
        const stats = await statsRes.json();

        // 获取数据集
        const dataRes = await fetch(`/api/data/full?page=${page}&per_page=30`);
        const data = await dataRes.json();

        currentDataPage = data.page;
        totalDataPages = data.pages;

        // 缓存数据用于预测
        allSamplesCache = data.data;

        // 渲染表格
        renderDataTable(data.data);

        // 渲染分页
        renderPagination(data.page, data.pages, data.total);

    } catch (e) {
        console.error('数据集加载失败:', e);
    }
}

function renderDataTable(samples) {
    const tbody = document.getElementById('dataTableBody');

    // 先显示原始数据
    let html = samples.map((s, i) => {
        const label = s.sentiment === 1 ? '积极' : '消极';
        const labelClass = s.sentiment === 1 ? 'text-success' : 'text-danger';
        return `
            <tr id="dataRow${i}">
                <td>${(currentDataPage - 1) * 30 + i + 1}</td>
                <td class="text-truncate" style="max-width:400px;">${s.comment || ''}</td>
                <td class="${labelClass} fw-bold">${label}</td>
                <td id="dataPred${i}"><small class="text-muted">分析中...</small></td>
                <td id="dataConf${i}"></td>
            </tr>
        `;
    }).join('');

    tbody.innerHTML = html;

    // 异步批量预测
    predictAndUpdateTable(samples);
}

async function predictAndUpdateTable(samples) {
    const texts = samples.map(s => s.comment || '');
    try {
        const res = await fetch('/api/predict_batch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ texts })
        });
        const data = await res.json();

        data.results.forEach((r, i) => {
            const predEl = document.getElementById('dataPred' + i);
            const confEl = document.getElementById('dataConf' + i);
            if (predEl) {
                const isCorrect = (r.label === samples[i].sentiment);
                predEl.innerHTML = `<span class="tag tag-${r.sentiment}">${r.sentiment_zh}</span>
                                    ${isCorrect ? '<span class="badge bg-success ms-1">✓ 正确</span>'
                                               : '<span class="badge bg-danger ms-1">✗ 错误</span>'}`;
            }
            if (confEl) {
                confEl.textContent = (r.confidence * 100).toFixed(1) + '%';
            }
        });
    } catch (e) {
        console.error('批量预测失败:', e);
    }
}

function renderPagination(current, total, count) {
    const container = document.getElementById('dataPagination');
    let html = `
        <li class="page-item ${current <= 1 ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="loadDatasetPage(${current - 1})">上一页</a>
        </li>
    `;

    for (let p = 1; p <= Math.min(total, 10); p++) {
        html += `
            <li class="page-item ${p === current ? 'active' : ''}">
                <a class="page-link" href="#" onclick="loadDatasetPage(${p})">${p}</a>
            </li>
        `;
    }

    if (total > 10) {
        html += `<li class="page-item disabled"><span class="page-link">...${total}</span></li>`;
    }

    html += `
        <li class="page-item ${current >= total ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="loadDatasetPage(${current + 1})">下一页</a>
        </li>
        <li class="page-item disabled"><span class="page-link">共 ${count} 条</span></li>
    `;

    container.innerHTML = html;
}

// ==================== 模型信息 ====================

async function loadModelInfo() {
    try {
        const res = await fetch('/api/model/metadata');
        const data = await res.json();

        const tbody = document.getElementById('modelParamsTable').querySelector('tbody');
        const rows = [
            ['模型名称', data.model_name || 'bert-base-chinese'],
            ['分类数', data.num_labels || 2],
            ['训练样本', data.train_samples || '-'],
            ['验证样本', data.val_samples || '-'],
            ['测试样本', data.test_samples || '-'],
            ['测试准确率', data.test_accuracy ? (data.test_accuracy * 100).toFixed(2) + '%' : '-'],
            ['测试F1', data.test_f1 ? (data.test_f1 * 100).toFixed(2) + '%' : '-'],
            ['测试AUC', data.test_auc ? (data.test_auc * 100).toFixed(2) + '%' : '-'],
            ['训练耗时', data.train_time_minutes ? data.train_time_minutes + ' 分钟' : '-'],
            ['模型已加载', data.model_loaded ? '✅ 是' : '⚠️ 模拟模式'],
            ['运行设备', data.device || '-'],
        ];

        tbody.innerHTML = rows.map(([k, v]) => `
            <tr><td class="fw-bold" style="width:40%;">${k}</td><td>${v}</td></tr>
        `).join('');
    } catch (e) {
        console.error('模型信息加载失败:', e);
    }
}

// ==================== 响应式处理 ====================

window.addEventListener('resize', () => {
    Object.values(chartInstances).forEach(c => {
        try { c.resize(); } catch (e) { /* ignore */ }
    });
});
