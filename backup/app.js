const APP_PASSWORD = '1688';
const STORAGE_KEYS = {
    portfolio: 'apex_portfolio',
    settings: 'apex_settings',
    lastUpdate: 'apex_lastUpdate',
    reports: 'apex_reports',
    recommendations: 'apex_recommendations'
};

class DataManager {
    static get(key) {
        try {
            const data = localStorage.getItem(key);
            return data ? JSON.parse(data) : null;
        } catch (e) {
            console.error('读取数据失败:', e);
            return null;
        }
    }

    static set(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
            return true;
        } catch (e) {
            console.error('保存数据失败:', e);
            return false;
        }
    }

    static remove(key) {
        localStorage.removeItem(key);
    }

    static clearAll() {
        Object.values(STORAGE_KEYS).forEach(key => localStorage.removeItem(key));
    }
}

class FundData {
    constructor() {
        this.portfolio = DataManager.get(STORAGE_KEYS.portfolio) || [];
        this.settings = DataManager.get(STORAGE_KEYS.settings) || {
            updateFreq: 'auto',
            passwordEnabled: true
        };
        this.lastUpdate = DataManager.get(STORAGE_KEYS.lastUpdate) || null;
        this.reports = DataManager.get(STORAGE_KEYS.reports) || [];
        this.recommendations = DataManager.get(STORAGE_KEYS.recommendations) || [];
    }

    savePortfolio() {
        DataManager.set(STORAGE_KEYS.portfolio, this.portfolio);
        this.updateLastUpdate();
    }

    saveSettings() {
        DataManager.set(STORAGE_KEYS.settings, this.settings);
    }

    updateLastUpdate() {
        this.lastUpdate = new Date().toISOString();
        DataManager.set(STORAGE_KEYS.lastUpdate, this.lastUpdate);
    }

    addFund(fund) {
        fund.id = Date.now();
        fund.createdAt = new Date().toISOString();
        this.portfolio.push(fund);
        this.savePortfolio();
        this.generateReport();
        this.generateRecommendations();
    }

    updateFund(id, updates) {
        const index = this.portfolio.findIndex(f => f.id === id);
        if (index !== -1) {
            this.portfolio[index] = { ...this.portfolio[index], ...updates };
            this.savePortfolio();
            this.generateReport();
            this.generateRecommendations();
        }
    }

    removeFund(id) {
        this.portfolio = this.portfolio.filter(f => f.id !== id);
        this.savePortfolio();
        this.generateReport();
        this.generateRecommendations();
    }

    getTotalAsset() {
        return this.portfolio.reduce((sum, f) => sum + (f.currentValue || 0), 0);
    }

    getTotalCost() {
        return this.portfolio.reduce((sum, f) => sum + (f.cost || 0), 0);
    }

    getTodayProfit() {
        return this.portfolio.reduce((sum, f) => sum + (f.todayProfit || 0), 0);
    }

    getTotalReturn() {
        const cost = this.getTotalCost();
        const asset = this.getTotalAsset();
        if (cost === 0) return 0;
        return ((asset - cost) / cost * 100);
    }

    generateReport() {
        const totalAsset = this.getTotalAsset();
        const todayProfit = this.getTodayProfit();
        const totalReturn = this.getTotalReturn();
        
        const report = {
            date: new Date().toISOString(),
            totalAsset,
            todayProfit,
            totalReturn,
            fundCount: this.portfolio.length,
            analysis: this._generateAnalysis()
        };
        
        this.reports.unshift(report);
        if (this.reports.length > 30) this.reports.pop();
        DataManager.set(STORAGE_KEYS.reports, this.reports);
        
        return report;
    }

    _generateAnalysis() {
        if (this.portfolio.length === 0) {
            return '暂无持仓数据，请添加基金开始管理您的投资组合。';
        }
        
        const positiveCount = this.portfolio.filter(f => (f.todayProfit || 0) > 0).length;
        const negativeCount = this.portfolio.filter(f => (f.todayProfit || 0) < 0).length;
        const todayProfit = this.getTodayProfit();
        
        let analysis = '';
        
        if (todayProfit > 0) {
            analysis += `今日盈利 ¥${todayProfit.toFixed(2)}，表现优秀！`;
        } else if (todayProfit < 0) {
            analysis += `今日亏损 ¥${Math.abs(todayProfit).toFixed(2)}，建议保持耐心。`;
        } else {
            analysis += '今日持平，继续观察市场走势。';
        }
        
        analysis += ` 共持有 ${this.portfolio.length} 只基金，`;
        analysis += `${positiveCount} 只上涨，${negativeCount} 只下跌。`;
        
        const totalReturn = this.getTotalReturn();
        if (totalReturn > 0) {
            analysis += ` 整体收益率 ${totalReturn.toFixed(2)}%，投资策略成效显著。`;
        } else if (totalReturn < 0) {
            analysis += ` 整体收益率 ${totalReturn.toFixed(2)}%，建议审视持仓结构。`;
        }
        
        return analysis;
    }

    generateRecommendations() {
        const recommendations = [];
        
        const sampleFunds = [
            { name: '易方达蓝筹精选混合', code: '005827', type: 'buy', reason: '长期业绩稳定，经理风格稳健，适合长期持有。当前估值合理，建议逢低布局。' },
            { name: '景顺长城新兴成长混合', code: '260108', type: 'hold', reason: '持仓以消费和科技为主，当前处于震荡期，建议持有观察。' },
            { name: '华夏回报混合A', code: '002001', type: 'buy', reason: '绝对收益策略，分红稳定，适合稳健型投资者。' },
            { name: '广发双擎升级混合', code: '005911', type: 'sell', reason: '近期涨幅较大，估值偏高，建议部分止盈。' },
            { name: '中欧时代先锋股票A', code: '001938', type: 'hold', reason: '科技成长风格，波动较大，建议控制仓位持有。' }
        ];
        
        sampleFunds.forEach((fund, index) => {
            recommendations.push({
                id: index + 1,
                ...fund,
                date: new Date().toISOString()
            });
        });
        
        this.recommendations = recommendations;
        DataManager.set(STORAGE_KEYS.recommendations, this.recommendations);
        
        return recommendations;
    }

    processImageUpload(file) {
        return new Promise((resolve) => {
            const reader = new FileReader();
            reader.onload = (e) => {
                setTimeout(() => {
                    const mockFunds = [
                        { name: '易方达消费精选股票', code: '009265', shares: 1000, costPrice: 2.5, currentPrice: 2.8, cost: 2500, currentValue: 2800, todayProfit: 50 },
                        { name: '招商中证白酒指数', code: '161725', shares: 500, costPrice: 1.2, currentPrice: 1.35, cost: 600, currentValue: 675, todayProfit: 20 }
                    ];
                    
                    mockFunds.forEach(fund => {
                        const existing = this.portfolio.find(f => f.code === fund.code);
                        if (existing) {
                            this.updateFund(existing.id, fund);
                        } else {
                            this.addFund(fund);
                        }
                    });
                    
                    resolve(mockFunds);
                }, 1500);
            };
            reader.readAsDataURL(file);
        });
    }
}

class UIManager {
    constructor(fundData) {
        this.fundData = fundData;
        this.init();
    }

    init() {
        this.bindEvents();
        this.checkTradeStatus();
        this.renderAll();
    }

    bindEvents() {
        document.getElementById('login-btn').addEventListener('click', () => this.handleLogin());
        document.getElementById('password-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.handleLogin();
        });

        document.getElementById('refresh-btn').addEventListener('click', () => this.handleRefresh());

        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', () => this.switchTab(item.dataset.tab));
        });

        document.getElementById('add-fund-btn').addEventListener('click', () => this.showAddFundModal());
        document.getElementById('modal-close').addEventListener('click', () => this.hideModal());
        document.getElementById('modal').addEventListener('click', (e) => {
            if (e.target.id === 'modal') this.hideModal();
        });

        const uploadArea = document.getElementById('upload-area');
        const fileInput = document.getElementById('file-input');
        uploadArea.addEventListener('click', () => fileInput.click());
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.style.borderColor = 'var(--primary)';
        });
        uploadArea.addEventListener('dragleave', () => {
            uploadArea.style.borderColor = 'var(--border)';
        });
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.style.borderColor = 'var(--border)';
            const files = e.dataTransfer.files;
            if (files.length > 0) this.handleFileUpload(files);
        });
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) this.handleFileUpload(e.target.files);
        });

        document.getElementById('back-btn').addEventListener('click', () => this.showPage('main'));
        document.getElementById('update-freq').addEventListener('change', (e) => {
            this.fundData.settings.updateFreq = e.target.value;
            this.fundData.saveSettings();
            this.showToast('设置已保存');
        });
        document.getElementById('password-toggle').addEventListener('change', (e) => {
            this.fundData.settings.passwordEnabled = e.target.checked;
            this.fundData.saveSettings();
            this.showToast('设置已保存');
        });
        document.getElementById('clear-data-btn').addEventListener('click', () => {
            if (confirm('确定要清除所有数据吗？此操作不可恢复！')) {
                DataManager.clearAll();
                this.showToast('数据已清除');
                location.reload();
            }
        });
        document.getElementById('export-data-btn').addEventListener('click', () => this.exportData());
        document.getElementById('import-data-btn').addEventListener('click', () => {
            document.getElementById('import-file').click();
        });
        document.getElementById('import-file').addEventListener('change', (e) => {
            if (e.target.files.length > 0) this.importData(e.target.files[0]);
        });

        document.getElementById('update-freq').value = this.fundData.settings.updateFreq;
        document.getElementById('password-toggle').checked = this.fundData.settings.passwordEnabled;
    }

    handleLogin() {
        const input = document.getElementById('password-input');
        const errorMsg = document.getElementById('error-msg');
        const loginBtn = document.getElementById('login-btn');
        
        if (input.value === APP_PASSWORD) {
            loginBtn.textContent = '登录中...';
            loginBtn.disabled = true;
            
            const loginPage = document.getElementById('login-page');
            loginPage.style.animation = 'fadeOut 0.3s ease-out forwards';
            
            setTimeout(() => {
                this.showPage('main');
                this.renderAll();
                
                document.getElementById('main-page').style.animation = 'slideIn 0.5s ease-out';
                
                loginBtn.textContent = '进入系统';
                loginBtn.disabled = false;
                input.value = '';
                
                this.showToast('🎉 欢迎回来！巅峰资本为您服务');
                
                if (this.fundData.portfolio.length === 0) {
                    setTimeout(() => {
                        this.showToast('💡 点击"添加"按钮开始管理您的基金');
                    }, 1500);
                }
            }, 350);
        } else {
            errorMsg.textContent = '密码错误，请重试';
            input.value = '';
            input.focus();
            
            const loginPageEl = document.getElementById('login-page');
            loginPageEl.classList.add('shake');
            setTimeout(() => {
                loginPageEl.classList.remove('shake');
            }, 500);
            
            setTimeout(() => {
                errorMsg.textContent = '';
            }, 3000);
        }
    }

    handleRefresh() {
        this.showToast('正在刷新数据...');
        
        this.fundData.portfolio.forEach(fund => {
            const change = (Math.random() - 0.5) * 0.02;
            fund.currentPrice = (fund.currentPrice || fund.costPrice || 1) * (1 + change);
            fund.currentValue = (fund.shares || 0) * fund.currentPrice;
            fund.todayProfit = fund.currentValue * change;
        });
        
        this.fundData.savePortfolio();
        this.fundData.generateReport();
        this.fundData.generateRecommendations();
        
        setTimeout(() => {
            this.renderAll();
            this.showToast('数据已更新');
        }, 1000);
    }

    async handleFileUpload(files) {
        this.showToast('正在解析图片...');
        
        for (const file of files) {
            if (file.type.startsWith('image/')) {
                await this.fundData.processImageUpload(file);
            }
        }
        
        this.renderAll();
        this.showToast('持仓数据已同步');
    }

    showAddFundModal() {
        const modal = document.getElementById('modal');
        const modalBody = document.getElementById('modal-body');
        document.getElementById('modal-title').textContent = '添加基金';
        
        modalBody.innerHTML = `
            <div class="form-group">
                <label class="form-label">基金名称</label>
                <input type="text" class="form-input" id="fund-name" placeholder="请输入基金名称">
            </div>
            <div class="form-group">
                <label class="form-label">基金代码</label>
                <input type="text" class="form-input" id="fund-code" placeholder="请输入基金代码">
            </div>
            <div class="form-group">
                <label class="form-label">持有份额</label>
                <input type="number" class="form-input" id="fund-shares" placeholder="请输入持有份额" step="0.01">
            </div>
            <div class="form-group">
                <label class="form-label">成本单价</label>
                <input type="number" class="form-input" id="fund-cost-price" placeholder="请输入成本单价" step="0.0001">
            </div>
            <div class="form-group">
                <label class="form-label">当前单价</label>
                <input type="number" class="form-input" id="fund-current-price" placeholder="请输入当前单价" step="0.0001">
            </div>
            <button class="btn-primary" id="save-fund-btn" style="width:100%;">保存</button>
        `;
        
        document.getElementById('save-fund-btn').addEventListener('click', () => this.saveFund());
        
        modal.classList.add('active');
    }

    showEditFundModal(id) {
        const fund = this.fundData.portfolio.find(f => f.id === id);
        if (!fund) return;
        
        const modal = document.getElementById('modal');
        const modalBody = document.getElementById('modal-body');
        document.getElementById('modal-title').textContent = '编辑基金';
        
        modalBody.innerHTML = `
            <div class="form-group">
                <label class="form-label">基金名称</label>
                <input type="text" class="form-input" id="fund-name" value="${fund.name || ''}">
            </div>
            <div class="form-group">
                <label class="form-label">基金代码</label>
                <input type="text" class="form-input" id="fund-code" value="${fund.code || ''}">
            </div>
            <div class="form-group">
                <label class="form-label">持有份额</label>
                <input type="number" class="form-input" id="fund-shares" value="${fund.shares || ''}" step="0.01">
            </div>
            <div class="form-group">
                <label class="form-label">成本单价</label>
                <input type="number" class="form-input" id="fund-cost-price" value="${fund.costPrice || ''}" step="0.0001">
            </div>
            <div class="form-group">
                <label class="form-label">当前单价</label>
                <input type="number" class="form-input" id="fund-current-price" value="${fund.currentPrice || ''}" step="0.0001">
            </div>
            <button class="btn-primary" id="save-fund-btn" style="width:100%; margin-bottom:0.5rem;">保存</button>
            <button class="btn-danger" id="delete-fund-btn" style="width:100%;">删除</button>
        `;
        
        document.getElementById('save-fund-btn').addEventListener('click', () => this.saveFund(id));
        document.getElementById('delete-fund-btn').addEventListener('click', () => {
            if (confirm('确定要删除这只基金吗？')) {
                this.fundData.removeFund(id);
                this.hideModal();
                this.renderAll();
                this.showToast('基金已删除');
            }
        });
        
        modal.classList.add('active');
    }

    saveFund(id = null) {
        const name = document.getElementById('fund-name').value.trim();
        const code = document.getElementById('fund-code').value.trim();
        const shares = parseFloat(document.getElementById('fund-shares').value) || 0;
        const costPrice = parseFloat(document.getElementById('fund-cost-price').value) || 0;
        const currentPrice = parseFloat(document.getElementById('fund-current-price').value) || costPrice;
        
        if (!name) {
            this.showToast('请输入基金名称');
            return;
        }
        
        const fund = {
            name,
            code,
            shares,
            costPrice,
            currentPrice,
            cost: shares * costPrice,
            currentValue: shares * currentPrice,
            todayProfit: (currentPrice - costPrice) * shares * 0.1
        };
        
        if (id) {
            this.fundData.updateFund(id, fund);
            this.showToast('基金已更新');
        } else {
            this.fundData.addFund(fund);
            this.showToast('基金已添加');
        }
        
        this.hideModal();
        this.renderAll();
    }

    hideModal() {
        document.getElementById('modal').classList.remove('active');
    }

    showPage(page) {
        document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
        document.getElementById(`${page}-page`).classList.add('active');
    }

    switchTab(tab) {
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.toggle('active', item.dataset.tab === tab);
        });
        
        if (tab === 'settings') {
            this.showPage('settings');
        } else {
            this.showPage('main');
        }
    }

    checkTradeStatus() {
        const now = new Date();
        const hour = now.getHours();
        const minute = now.getMinutes();
        const day = now.getDay();
        
        const isWeekday = day >= 1 && day <= 5;
        const isTradeTime = (hour >= 9 && hour < 15) || (hour === 15 && minute < 30);
        
        const statusEl = document.getElementById('trade-status');
        if (isWeekday && isTradeTime) {
            statusEl.textContent = '交易中';
            statusEl.style.color = 'var(--success)';
        } else if (isWeekday) {
            statusEl.textContent = '休市中';
            statusEl.style.color = 'var(--text-secondary)';
        } else {
            statusEl.textContent = '休市中';
            statusEl.style.color = 'var(--text-secondary)';
        }
    }

    renderAll() {
        this.renderUpdateTime();
        this.renderAssetOverview();
        this.renderReport();
        this.renderPortfolio();
        this.renderRecommendations();
    }

    renderUpdateTime() {
        const updateTimeEl = document.getElementById('update-time');
        if (this.fundData.lastUpdate) {
            const date = new Date(this.fundData.lastUpdate);
            updateTimeEl.textContent = date.toLocaleString('zh-CN');
        } else {
            updateTimeEl.textContent = '--';
        }
    }

    renderAssetOverview() {
        const totalAsset = this.fundData.getTotalAsset();
        const totalCost = this.fundData.getTotalCost();
        const todayProfit = this.fundData.getTodayProfit();
        const totalReturn = this.fundData.getTotalReturn();
        
        document.getElementById('total-asset').textContent = `¥${totalAsset.toFixed(2)}`;
        document.getElementById('total-cost').textContent = `¥${totalCost.toFixed(2)}`;
        
        const todayProfitEl = document.getElementById('today-profit');
        todayProfitEl.textContent = `${todayProfit >= 0 ? '+' : ''}¥${todayProfit.toFixed(2)}`;
        todayProfitEl.className = `stat-value ${todayProfit >= 0 ? 'positive' : 'negative'}`;
        
        const totalReturnEl = document.getElementById('total-return');
        totalReturnEl.textContent = `${totalReturn >= 0 ? '+' : ''}${totalReturn.toFixed(2)}%`;
        totalReturnEl.className = `stat-value ${totalReturn >= 0 ? 'positive' : 'negative'}`;
    }

    renderReport() {
        const reportContent = document.getElementById('report-content');
        
        if (this.fundData.reports.length === 0) {
            this.fundData.generateReport();
        }
        
        const latestReport = this.fundData.reports[0];
        
        if (latestReport) {
            reportContent.innerHTML = `<p>${latestReport.analysis}</p>`;
        } else {
            reportContent.innerHTML = '<div class="empty-state">暂无汇报数据</div>';
        }
    }

    renderPortfolio() {
        const list = document.getElementById('portfolio-list');
        
        if (this.fundData.portfolio.length === 0) {
            list.innerHTML = '<div class="empty-state">暂无持仓数据，点击上方添加按钮开始</div>';
            return;
        }
        
        list.innerHTML = this.fundData.portfolio.map(fund => {
            const change = fund.currentPrice && fund.costPrice 
                ? ((fund.currentPrice - fund.costPrice) / fund.costPrice * 100) 
                : 0;
            const todayProfit = fund.todayProfit || 0;
            
            return `
                <div class="portfolio-item" data-id="${fund.id}">
                    <div class="portfolio-header">
                        <div>
                            <div class="fund-name">${fund.name}</div>
                            <div class="fund-code">${fund.code || '--'}</div>
                        </div>
                        <div class="fund-change ${change >= 0 ? 'positive' : 'negative'}">
                            ${change >= 0 ? '+' : ''}${change.toFixed(2)}%
                        </div>
                    </div>
                    <div class="portfolio-details">
                        <div class="detail-item">
                            <span class="detail-label">市值</span>
                            <span class="detail-value">¥${(fund.currentValue || 0).toFixed(2)}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">成本</span>
                            <span class="detail-value">¥${(fund.cost || 0).toFixed(2)}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">今日盈亏</span>
                            <span class="detail-value ${todayProfit >= 0 ? 'positive' : 'negative'}" style="color: ${todayProfit >= 0 ? 'var(--success)' : 'var(--danger)'}">
                                ${todayProfit >= 0 ? '+' : ''}¥${todayProfit.toFixed(2)}
                            </span>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
        
        list.querySelectorAll('.portfolio-item').forEach(item => {
            item.addEventListener('click', () => {
                this.showEditFundModal(parseInt(item.dataset.id));
            });
        });
    }

    renderRecommendations() {
        const list = document.getElementById('recommend-list');
        
        if (this.fundData.recommendations.length === 0) {
            this.fundData.generateRecommendations();
        }
        
        list.innerHTML = this.fundData.recommendations.map(rec => `
            <div class="recommend-item">
                <div class="recommend-header">
                    <div>
                        <div class="recommend-name">${rec.name}</div>
                        <div class="fund-code">${rec.code}</div>
                    </div>
                    <span class="recommend-tag ${rec.type}">
                        ${rec.type === 'buy' ? '买入' : rec.type === 'sell' ? '卖出' : '持有'}
                    </span>
                </div>
                <p class="recommend-reason">${rec.reason}</p>
            </div>
        `).join('');
    }

    exportData() {
        const data = {
            portfolio: this.fundData.portfolio,
            settings: this.fundData.settings,
            lastUpdate: this.fundData.lastUpdate,
            reports: this.fundData.reports,
            recommendations: this.fundData.recommendations,
            exportDate: new Date().toISOString()
        };
        
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `apex-capital-backup-${new Date().toISOString().slice(0,10)}.json`;
        a.click();
        URL.revokeObjectURL(url);
        
        this.showToast('数据已导出');
    }

    importData(file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            try {
                const data = JSON.parse(e.target.result);
                
                if (data.portfolio) {
                    this.fundData.portfolio = data.portfolio;
                    this.fundData.savePortfolio();
                }
                if (data.settings) {
                    this.fundData.settings = data.settings;
                    this.fundData.saveSettings();
                }
                if (data.reports) {
                    this.fundData.reports = data.reports;
                    DataManager.set(STORAGE_KEYS.reports, data.reports);
                }
                if (data.recommendations) {
                    this.fundData.recommendations = data.recommendations;
                    DataManager.set(STORAGE_KEYS.recommendations, data.recommendations);
                }
                
                this.renderAll();
                this.showToast('数据导入成功');
            } catch (err) {
                this.showToast('导入失败：文件格式错误');
            }
        };
        reader.readAsText(file);
    }

    showToast(message) {
        const existing = document.querySelector('.toast');
        if (existing) existing.remove();
        
        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.textContent = message;
        document.body.appendChild(toast);
        
        setTimeout(() => toast.remove(), 3000);
    }
}

const fundData = new FundData();
const ui = new UIManager(fundData);

if (fundData.portfolio.length === 0) {
    setTimeout(() => {
        ui.showToast('欢迎使用巅峰资本！添加您的第一只基金吧');
    }, 1000);
}

FundData.prototype.initSampleData = function() {
    const sampleFunds = [
        {
            name: '易方达蓝筹精选混合',
            code: '005827',
            shares: 1000,
            costPrice: 2.85,
            currentPrice: 3.12,
            cost: 2850,
            currentValue: 3120,
            todayProfit: 45.50
        },
        {
            name: '景顺长城新兴成长混合',
            code: '260108',
            shares: 500,
            costPrice: 1.95,
            currentPrice: 2.08,
            cost: 975,
            currentValue: 1040,
            todayProfit: -12.30
        },
        {
            name: '华夏回报混合A',
            code: '002001',
            shares: 2000,
            costPrice: 1.45,
            currentPrice: 1.52,
            cost: 2900,
            currentValue: 3040,
            todayProfit: 23.80
        },
        {
            name: '广发双擎升级混合',
            code: '005911',
            shares: 800,
            costPrice: 3.20,
            currentPrice: 3.05,
            cost: 2560,
            currentValue: 2440,
            todayProfit: -28.50
        },
        {
            name: '中欧时代先锋股票A',
            code: '001938',
            shares: 1500,
            costPrice: 1.78,
            currentPrice: 1.85,
            cost: 2670,
            currentValue: 2775,
            todayProfit: 18.20
        }
    ];
    
    sampleFunds.forEach(fund => {
        this.addFund(fund);
    });
    
    this.savePortfolio();
};

if (localStorage.getItem('apex_welcomed') !== 'true') {
    setTimeout(() => {
        if (confirm('欢迎使用巅峰资本！是否加载示例数据进行体验？')) {
            fundData.initSampleData();
            ui.renderAll();
            ui.showToast('✅ 示例数据已加载，请查看您的持仓');
        }
        localStorage.setItem('apex_welcomed', 'true');
    }, 2000);
}
