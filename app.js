const APP_PASSWORD = '1688';
const POLL_INTERVAL = 5 * 60 * 1000;
const DATA_URL = 'data.json';
const VERSION_URL = 'data_version.json';

const STORAGE_KEYS = {
    settings: 'apex_settings',
    localFunds: 'apex_local_funds',
    lastVisit: 'apex_last_visit'
};

class DataLoader {
    constructor() {
        this.cloudData = null;
        this.currentVersion = null;
        this.pollTimer = null;
        this.listeners = [];
    }

    onChange(fn) { this.listeners.push(fn); }

    _notify() {
        this.listeners.forEach(fn => fn(this.cloudData));
    }

    async load() {
        try {
            const versionResp = await fetch(VERSION_URL, { cache: 'no-store' });
            if (versionResp.ok) {
                const v = await versionResp.json();
                this.currentVersion = v.v;
            }
        } catch (e) { /* version file optional */ }

        const url = this.currentVersion
            ? `${DATA_URL}?v=${this.currentVersion}`
            : `${DATA_URL}?t=${Date.now()}`;

        const resp = await fetch(url, { cache: 'no-store' });
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        this.cloudData = await resp.json();
        this._notify();
        return this.cloudData;
    }

    async checkForUpdate() {
        try {
            const resp = await fetch(VERSION_URL, { cache: 'no-store' });
            if (!resp.ok) return false;
            const v = await resp.json();
            if (v.v !== this.currentVersion) {
                this.currentVersion = v.v;
                await this.load();
                return true;
            }
        } catch (e) { /* ignore */ }
        return false;
    }

    startPolling() {
        this.stopPolling();
        this.pollTimer = setInterval(() => this.checkForUpdate(), POLL_INTERVAL);
    }

    stopPolling() {
        if (this.pollTimer) {
            clearInterval(this.pollTimer);
            this.pollTimer = null;
        }
    }
}

class Settings {
    static get() {
        try {
            return JSON.parse(localStorage.getItem(STORAGE_KEYS.settings)) || {};
        } catch (e) { return {}; }
    }
    static set(obj) {
        localStorage.setItem(STORAGE_KEYS.settings, JSON.stringify(obj));
    }
    static getLocalFunds() {
        try {
            return JSON.parse(localStorage.getItem(STORAGE_KEYS.localFunds)) || [];
        } catch (e) { return []; }
    }
    static setLocalFunds(funds) {
        localStorage.setItem(STORAGE_KEYS.localFunds, JSON.stringify(funds));
    }
}

class UIManager {
    constructor() {
        this.loader = new DataLoader();
        this.localFunds = Settings.getLocalFunds();
        this.isLoggedIn = false;
        this.init();
    }

    init() {
        this.bindEvents();
        this.loader.onChange(data => this.onDataLoaded(data));
        this.showLoading(true);
        this.loader.load()
            .then(() => { this.loader.startPolling(); })
            .catch(err => this.onLoadError(err));
    }

    // ── Event Binding ──

    bindEvents() {
        document.getElementById('login-btn').addEventListener('click', () => this.handleLogin());
        document.getElementById('password-input').addEventListener('keypress', e => {
            if (e.key === 'Enter') this.handleLogin();
        });
        document.getElementById('refresh-btn').addEventListener('click', () => this.handleRefresh());
        document.getElementById('add-fund-btn').addEventListener('click', () => this.showAddFundModal());
        document.getElementById('modal-close').addEventListener('click', () => this.hideModal());
        document.getElementById('modal').addEventListener('click', e => {
            if (e.target.id === 'modal') this.hideModal();
        });
        document.getElementById('back-btn').addEventListener('click', () => this.showPage('main'));
        document.getElementById('clear-data-btn').addEventListener('click', () => {
            if (confirm('确定要清除所有本地数据吗？云端数据不受影响。')) {
                localStorage.clear();
                this.localFunds = [];
                this.showToast('本地数据已清除');
                this.renderLocalPortfolio();
            }
        });
        document.getElementById('export-data-btn').addEventListener('click', () => this.exportData());
        document.getElementById('import-data-btn').addEventListener('click', () => {
            document.getElementById('import-file').click();
        });
        document.getElementById('import-file').addEventListener('change', e => {
            if (e.target.files.length > 0) this.importData(e.target.files[0]);
        });
        document.getElementById('retry-btn').addEventListener('click', () => {
            this.showLoading(true);
            this.showError(false);
            this.loader.load()
                .then(() => this.loader.startPolling())
                .catch(err => this.onLoadError(err));
        });
        document.getElementById('error-banner-close').addEventListener('click', () => {
            this.showError(false);
        });
        document.getElementById('stale-banner-close').addEventListener('click', () => {
            document.getElementById('stale-banner').style.display = 'none';
        });
    }

    // ── Login ──

    handleLogin() {
        const input = document.getElementById('password-input');
        const errorMsg = document.getElementById('error-msg');
        const loginBtn = document.getElementById('login-btn');

        if (input.value === APP_PASSWORD) {
            this.isLoggedIn = true;
            loginBtn.textContent = '登录中...';
            loginBtn.disabled = true;
            const loginPage = document.getElementById('login-page');
            loginPage.style.animation = 'fadeOut 0.3s ease-out forwards';
            setTimeout(() => {
                this.showPage('main');
                document.getElementById('main-page').style.animation = 'slideIn 0.5s ease-out';
                loginBtn.textContent = '进入系统';
                loginBtn.disabled = false;
                input.value = '';
                this.showToast('欢迎回来！巅峰资本为您服务');
                if (this.loader.cloudData) this.renderAll();
            }, 350);
        } else {
            errorMsg.textContent = '密码错误，请重试';
            input.value = '';
            input.focus();
            const loginPageEl = document.getElementById('login-page');
            loginPageEl.classList.add('shake');
            setTimeout(() => loginPageEl.classList.remove('shake'), 500);
            setTimeout(() => { errorMsg.textContent = ''; }, 3000);
        }
    }

    // ── Data Loading ──

    onDataLoaded(data) {
        this.showLoading(false);
        this.showError(false);
        this.renderAll();
    }

    onLoadError(err) {
        this.showLoading(false);
        this.showError(true);
        console.error('数据加载失败:', err);
    }

    async handleRefresh() {
        const btn = document.getElementById('refresh-btn');
        btn.style.animation = 'spin 0.8s linear';
        this.showToast('正在刷新数据...');

        try {
            const updated = await this.loader.checkForUpdate();
            if (!updated && this.loader.cloudData) {
                this.renderAll();
                this.showToast('数据已是最新');
            } else if (updated) {
                this.showToast('数据已更新');
            }
        } catch (e) {
            try {
                await this.loader.load();
                this.showToast('数据已更新');
            } catch (e2) {
                this.showToast('刷新失败，请检查网络');
            }
        }

        setTimeout(() => { btn.style.animation = ''; }, 800);
    }

    // ── UI State ──

    showLoading(visible) {
        document.getElementById('loading-overlay').style.display = visible ? 'flex' : 'none';
    }

    showError(visible) {
        document.getElementById('error-banner').style.display = visible ? 'block' : 'none';
    }

    showPage(page) {
        document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
        const target = document.getElementById(`${page}-page`);
        if (target) target.classList.add('active');
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

    // ── Render All ──

    renderAll() {
        const d = this.loader.cloudData;
        if (!d) return;
        this.renderHeader(d);
        this.renderStaleBanner(d);
        this.renderAssetOverview(d);
        this.renderTypeDistribution(d);
        this.renderReport(d);
        this.renderPortfolio(d);
        this.renderRankings(d);
        this.renderLocalPortfolio();
    }

    // ── Header ──

    renderHeader(d) {
        document.getElementById('update-time').textContent = this._formatTime(d.update_time);
        document.getElementById('trade-status').textContent = d.trading_status || '未知';
        const statusEl = document.getElementById('trade-status');
        if (d.trading_status === '交易中') {
            statusEl.style.color = 'var(--success)';
        } else {
            statusEl.style.color = 'var(--text-secondary)';
        }
    }

    _formatTime(timeStr) {
        if (!timeStr) return '--';
        try {
            const t = new Date(timeStr.replace(' ', 'T'));
            const now = new Date();
            const diff = Math.floor((now - t) / 1000);
            const abs = t.toLocaleString('zh-CN', { hour12: false });
            if (diff < 60) return `刚刚 (${abs})`;
            if (diff < 3600) return `${Math.floor(diff / 60)}分钟前 (${abs})`;
            if (diff < 86400) return `${Math.floor(diff / 3600)}小时前 (${abs})`;
            return `${Math.floor(diff / 86400)}天前 (${abs})`;
        } catch (e) {
            return timeStr;
        }
    }

    // ── Stale Banner ──

    renderStaleBanner(d) {
        const banner = document.getElementById('stale-banner');
        const msgEl = document.getElementById('stale-msg');
        if (d.data_stale && d.data_stale.level !== 'none') {
            banner.className = 'stale-banner ' + d.data_stale.level;
            msgEl.textContent = d.data_stale.msg;
            banner.style.display = 'flex';
        } else {
            banner.style.display = 'none';
        }
    }

    // ── Asset Overview ──

    renderAssetOverview(d) {
        const s = d.summary;
        document.getElementById('total-asset').textContent = `¥${s.total_value.toLocaleString('zh-CN', { minimumFractionDigits: 2 })}`;

        const todayEl = document.getElementById('today-profit');
        const todayVal = s.today_pnl;
        todayEl.textContent = `${todayVal >= 0 ? '+' : ''}¥${todayVal.toLocaleString('zh-CN', { minimumFractionDigits: 2 })}`;
        todayEl.className = `stat-value ${todayVal >= 0 ? 'positive' : 'negative'}`;

        document.getElementById('total-cost').textContent =
            `¥${s.total_cost.toLocaleString('zh-CN', { minimumFractionDigits: 2 })}`;

        const retEl = document.getElementById('total-return');
        const retVal = s.total_hold_pnl_pct;
        retEl.textContent = `${retVal >= 0 ? '+' : ''}${retVal.toFixed(2)}%`;
        retEl.className = `stat-value ${retVal >= 0 ? 'positive' : 'negative'}`;

        // Sub-stats: normal vs pension
        document.getElementById('normal-value').textContent =
            `¥${s.normal_value.toLocaleString('zh-CN', { minimumFractionDigits: 2 })}`;
        document.getElementById('pension-value').textContent =
            `¥${s.pension_value.toLocaleString('zh-CN', { minimumFractionDigits: 2 })}`;
        document.getElementById('normal-today').textContent =
            `${s.normal_today_pnl >= 0 ? '+' : ''}¥${s.normal_today_pnl.toFixed(2)}`;
        document.getElementById('pension-today').textContent =
            `${s.pension_today_pnl >= 0 ? '+' : ''}¥${s.pension_today_pnl.toFixed(2)}`;
    }

    // ── Type Distribution ──

    renderTypeDistribution(d) {
        const types = d.type_distribution;
        if (!types) return;
        const container = document.getElementById('type-distribution');
        const maxVal = Math.max(...Object.values(types).map(t => t.value));

        container.innerHTML = Object.entries(types).map(([key, t]) => {
            const width = maxVal > 0 ? (t.value / maxVal * 100) : 0;
            const labels = { qdii: 'QDII', mix: '混合', index: '指数', stock: '股票', fof: 'FOF', bond: '债券' };
            return `
                <div class="type-row">
                    <span class="type-label">${labels[key] || key}</span>
                    <div class="type-bar-track">
                        <div class="type-bar-fill" style="width:${width}%"></div>
                    </div>
                    <span class="type-value">¥${(t.value / 10000).toFixed(1)}万 (${t.pct}%)</span>
                </div>`;
        }).join('');
    }

    // ── Report ──

    renderReport(d) {
        const el = document.getElementById('report-content');
        if (d.report_text) {
            el.innerHTML = d.report_text.split('\n').map(line =>
                line ? `<p>${this._escapeHtml(line)}</p>` : '<br>'
            ).join('');
        } else {
            el.innerHTML = '<div class="empty-state">暂无汇报数据</div>';
        }
    }

    _escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    // ── Portfolio (Cloud) ──

    renderPortfolio(d) {
        const list = document.getElementById('portfolio-list');
        const funds = d.funds || [];

        if (funds.length === 0) {
            list.innerHTML = '<div class="empty-state">暂无持仓数据</div>';
            return;
        }

        list.innerHTML = funds.map(f => {
            const changeClass = f.today_pct >= 0 ? 'positive' : 'negative';
            const profitClass = f.hold_pnl >= 0 ? 'positive' : 'negative';
            const warnings = (f.warnings || []).map(w => `<span class="fund-warning">${w}</span>`).join('');
            const pensionBadge = f.is_pension
                ? '<span class="pension-badge">养老</span>' : '';

            return `
                <div class="portfolio-item">
                    <div class="portfolio-header">
                        <div>
                            <div class="fund-name">${f.name}${pensionBadge}</div>
                            <div class="fund-meta">
                                <span class="fund-code">${f.code}</span>
                                <span class="fund-type-tag">${f.type || ''}</span>
                            </div>
                        </div>
                        <div class="fund-change ${changeClass}">
                            ${f.today_pct >= 0 ? '+' : ''}${f.today_pct.toFixed(2)}%
                        </div>
                    </div>
                    <div class="portfolio-details">
                        <div class="detail-item">
                            <span class="detail-label">市值</span>
                            <span class="detail-value">¥${f.market_value.toLocaleString('zh-CN', { minimumFractionDigits: 2 })}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">今日盈亏</span>
                            <span class="detail-value ${changeClass}" style="color:${f.today_pnl >= 0 ? 'var(--success)' : 'var(--danger)'}">
                                ${f.today_pnl >= 0 ? '+' : ''}¥${f.today_pnl.toFixed(2)}
                            </span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">持有收益</span>
                            <span class="detail-value ${profitClass}">
                                ${f.hold_pnl_pct >= 0 ? '+' : ''}${f.hold_pnl_pct.toFixed(2)}%
                            </span>
                        </div>
                    </div>
                    ${warnings ? `<div class="fund-warnings">${warnings}</div>` : ''}
                </div>`;
        }).join('');
    }

    // ── Rankings ──

    renderRankings(d) {
        const rankings = d.rankings;
        if (!rankings) return;

        const profitList = document.getElementById('top-profit-list');
        const lossList = document.getElementById('top-loss-list');

        if (rankings.top_profit) {
            profitList.innerHTML = rankings.top_profit.map((f, i) => `
                <div class="rank-item">
                    <span class="rank-num profit">${i + 1}</span>
                    <span class="rank-name">${f.name}</span>
                    <span class="rank-pct positive">+${f.pct.toFixed(2)}%</span>
                </div>`).join('');
        }

        if (rankings.top_loss) {
            lossList.innerHTML = rankings.top_loss.map((f, i) => `
                <div class="rank-item">
                    <span class="rank-num loss">${i + 1}</span>
                    <span class="rank-name">${f.name}</span>
                    <span class="rank-pct negative">${f.pct.toFixed(2)}%</span>
                </div>`).join('');
        }
    }

    // ── Local Portfolio ──

    renderLocalPortfolio() {
        const list = document.getElementById('local-portfolio-list');
        const section = document.getElementById('local-portfolio-section');

        if (!this.isLoggedIn) {
            section.style.display = 'none';
            return;
        }
        section.style.display = '';

        if (this.localFunds.length === 0) {
            list.innerHTML = '<div class="empty-state">暂无手动添加的基金</div>';
            return;
        }

        list.innerHTML = this.localFunds.map((f, idx) => {
            const val = (f.shares || 0) * (f.currentPrice || 0);
            const cost = (f.shares || 0) * (f.costPrice || 0);
            const pnl = val - cost;
            return `
                <div class="portfolio-item local" data-idx="${idx}">
                    <div class="portfolio-header">
                        <div>
                            <div class="fund-name">${f.name}</div>
                            <div class="fund-code">${f.code || '--'}</div>
                        </div>
                        <span class="fund-change ${pnl >= 0 ? 'positive' : 'negative'}">
                            ${pnl >= 0 ? '+' : ''}¥${pnl.toFixed(2)}
                        </span>
                    </div>
                    <div class="portfolio-details">
                        <div class="detail-item">
                            <span class="detail-label">市值</span>
                            <span class="detail-value">¥${val.toFixed(2)}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">成本</span>
                            <span class="detail-value">¥${cost.toFixed(2)}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">份额</span>
                            <span class="detail-value">${(f.shares || 0).toFixed(2)}</span>
                        </div>
                    </div>
                </div>`;
        }).join('');

        list.querySelectorAll('.portfolio-item.local').forEach(item => {
            item.addEventListener('click', () => {
                const idx = parseInt(item.dataset.idx);
                this.showEditLocalFundModal(idx);
            });
        });
    }

    showAddFundModal() {
        if (!this.isLoggedIn) {
            this.showToast('请先登录后再添加基金');
            return;
        }
        const modal = document.getElementById('modal');
        const modalBody = document.getElementById('modal-body');
        document.getElementById('modal-title').textContent = '添加基金（本地）';

        modalBody.innerHTML = `
            <p style="font-size:0.8rem;color:var(--text-secondary);margin-bottom:1rem;">
                手动添加的基金存储在本地，不会与云端数据同步。
            </p>
            <div class="form-group">
                <label class="form-label">基金名称 *</label>
                <input type="text" class="form-input" id="fund-name" placeholder="请输入基金名称">
            </div>
            <div class="form-group">
                <label class="form-label">基金代码</label>
                <input type="text" class="form-input" id="fund-code" placeholder="如 005827">
            </div>
            <div class="form-group">
                <label class="form-label">持有份额</label>
                <input type="number" class="form-input" id="fund-shares" placeholder="0" step="0.01">
            </div>
            <div class="form-group">
                <label class="form-label">成本单价</label>
                <input type="number" class="form-input" id="fund-cost-price" placeholder="0" step="0.0001">
            </div>
            <div class="form-group">
                <label class="form-label">当前单价</label>
                <input type="number" class="form-input" id="fund-current-price" placeholder="0" step="0.0001">
            </div>
            <button class="btn-primary" id="save-local-fund-btn" style="width:100%;">保存</button>
        `;

        document.getElementById('save-local-fund-btn').addEventListener('click', () => this.saveLocalFund());
        modal.classList.add('active');
    }

    showEditLocalFundModal(idx) {
        const fund = this.localFunds[idx];
        if (!fund) return;

        const modal = document.getElementById('modal');
        const modalBody = document.getElementById('modal-body');
        document.getElementById('modal-title').textContent = '编辑基金（本地）';

        modalBody.innerHTML = `
            <div class="form-group">
                <label class="form-label">基金名称</label>
                <input type="text" class="form-input" id="fund-name" value="${this._escapeAttr(fund.name || '')}">
            </div>
            <div class="form-group">
                <label class="form-label">基金代码</label>
                <input type="text" class="form-input" id="fund-code" value="${this._escapeAttr(fund.code || '')}">
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
            <button class="btn-primary" id="save-local-fund-btn" style="width:100%;margin-bottom:0.5rem;">保存</button>
            <button class="btn-danger" id="delete-local-fund-btn" style="width:100%;">删除</button>
        `;

        document.getElementById('save-local-fund-btn').addEventListener('click', () => this.saveLocalFund(idx));
        document.getElementById('delete-local-fund-btn').addEventListener('click', () => {
            if (confirm('确定要删除这只基金吗？')) {
                this.localFunds.splice(idx, 1);
                Settings.setLocalFunds(this.localFunds);
                this.hideModal();
                this.renderLocalPortfolio();
                this.showToast('基金已删除');
            }
        });
        modal.classList.add('active');
    }

    saveLocalFund(idx = null) {
        const name = document.getElementById('fund-name').value.trim();
        const code = document.getElementById('fund-code').value.trim();
        const shares = parseFloat(document.getElementById('fund-shares').value) || 0;
        const costPrice = parseFloat(document.getElementById('fund-cost-price').value) || 0;
        const currentPrice = parseFloat(document.getElementById('fund-current-price').value) || 0;

        if (!name) {
            this.showToast('请输入基金名称');
            return;
        }

        const fund = { name, code, shares, costPrice, currentPrice };

        if (idx !== null) {
            this.localFunds[idx] = fund;
        } else {
            this.localFunds.push(fund);
        }

        Settings.setLocalFunds(this.localFunds);
        this.hideModal();
        this.renderLocalPortfolio();
        this.showToast(idx !== null ? '基金已更新' : '基金已添加');
    }

    hideModal() {
        document.getElementById('modal').classList.remove('active');
    }

    _escapeAttr(str) {
        return str.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    // ── Data Export/Import ──

    exportData() {
        const data = {
            localFunds: this.localFunds,
            settings: Settings.get(),
            exportDate: new Date().toISOString()
        };
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `apex-capital-backup-${new Date().toISOString().slice(0, 10)}.json`;
        a.click();
        URL.revokeObjectURL(url);
        this.showToast('本地数据已导出');
    }

    importData(file) {
        const reader = new FileReader();
        reader.onload = e => {
            try {
                const data = JSON.parse(e.target.result);
                if (Array.isArray(data.localFunds)) {
                    this.localFunds = data.localFunds;
                    Settings.setLocalFunds(this.localFunds);
                }
                if (data.settings) Settings.set(data.settings);
                this.renderLocalPortfolio();
                this.showToast('数据导入成功');
            } catch (err) {
                this.showToast('导入失败：文件格式错误');
            }
        };
        reader.readAsText(file);
    }
}

// ── Boot ──

const ui = new UIManager();
