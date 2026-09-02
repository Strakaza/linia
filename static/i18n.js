const i18n = {
    currentLang: (function () {
        try {
            const path = window.location.pathname || '/';
            const segments = path.split('/').filter(Boolean);
            const candidate = segments.length > 0 ? segments[0].toLowerCase() : null;
            const supported = [
                'fr', 'en', 'de', 'es', 'pt', 'nl', 'sq', 'ca', 'hr', 'bg', 'da', 'et', 'fi',
                'el', 'hu', 'hi', 'lv', 'lt', 'lb', 'mk', 'ro', 'pl', 'cs', 'sk', 'sl', 'sv',
                'tr', 'uk', 'ru', 'be'
            ];
            if (candidate && supported.includes(candidate)) {
                return candidate;
            }
        } catch (e) {
            console.warn('i18n: unable to infer lang from URL', e);
        }

        const storedLang = localStorage.getItem('linia_lang');
        if (storedLang) return storedLang;

        try {
            const browserLang = navigator.language || navigator.userLanguage;
            if (browserLang) {
                const shortLang = browserLang.substring(0, 2).toLowerCase();
                const supported = [
                    'fr', 'en', 'de', 'es', 'pt', 'nl', 'sq', 'ca', 'hr', 'bg', 'da', 'et', 'fi',
                    'el', 'hu', 'hi', 'lv', 'lt', 'lb', 'mk', 'ro', 'pl', 'cs', 'sk', 'sl', 'sv',
                    'tr', 'uk', 'ru', 'be'
                ];
                if (supported.includes(shortLang)) {
                    return shortLang;
                }
            }
        } catch (e) {
            console.warn('i18n: unable to infer lang from Browser', e);
        }

        return 'fr';
    })(),
    SUPPORTED_LANGS: [
        'fr', 'en', 'de', 'es', 'pt', 'nl', 'sq', 'ca', 'hr', 'bg', 'da', 'et', 'fi',
        'el', 'hu', 'hi', 'lv', 'lt', 'lb', 'mk', 'ro', 'pl', 'cs', 'sk', 'sl', 'sv',
        'tr', 'uk', 'ru', 'be'
    ],
    t(key, params = {}) {
        const dict = window.TRANSLATIONS || {};
        let text = dict[key];
        if (params.count !== undefined && typeof params.count === 'number') {
            try {
                const pluralRules = new Intl.PluralRules(this.currentLang);
                const rule = pluralRules.select(params.count);
                const pluralKey = `${key}_${rule}`;
                if (dict[pluralKey]) {
                    text = dict[pluralKey];
                } else if (rule !== 'other' && dict[`${key}_other`]) {
                    text = dict[`${key}_other`];
                }
            } catch (e) {
                console.warn('i18n pluralization error:', e);
            }
        }
        if (!text) text = dict[key] || key;
        Object.keys(params).forEach(p => {
            const regex = new RegExp(`{${p}}`, 'g');
            text = text.replace(regex, params[p]);
        });
        return text;
    },
    setLang(lang) {
        if (!this.SUPPORTED_LANGS.includes(lang)) {
            console.error('Linia i18n: Unknown language', lang);
            lang = 'fr';
        }
        const path = window.location.pathname || '/';
        const segments = path.split('/').filter(Boolean);
        const supported = [
            'fr', 'en', 'de', 'es', 'pt', 'nl', 'sq', 'ca', 'hr', 'bg', 'da', 'et', 'fi',
            'el', 'hu', 'hi', 'lv', 'lt', 'lb', 'mk', 'ro', 'pl', 'cs', 'sk', 'sl', 'sv',
            'tr', 'uk', 'ru', 'be'
        ];
        let slugParts = segments;
        if (segments.length > 0 && supported.includes(segments[0])) {
            slugParts = segments.slice(1);
        }
        const slug = slugParts.join('/');
        let newPath;
        if (lang === 'fr') {
            newPath = slug ? `/${slug}` : '/';
        } else {
            newPath = slug ? `/${lang}/${slug}` : `/${lang}/`;
        }
        localStorage.setItem('linia_lang', lang);
        if (newPath !== path) {
            window.location.pathname = newPath;
        } else {
            this.currentLang = lang;
            this.translatePage();
            document.dispatchEvent(new CustomEvent('linia-lang-changed', { detail: lang }));
        }
    },
    translatePage() {
        document.querySelectorAll('[data-i18n]').forEach(el => {
            const key = el.getAttribute('data-i18n');
            el.textContent = this.t(key);
        });
        document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
            const key = el.getAttribute('data-i18n-placeholder');
            el.placeholder = this.t(key);
        });
        document.querySelectorAll('[data-i18n-title]').forEach(el => {
            const key = el.getAttribute('data-i18n-title');
            el.title = this.t(key);
        });
        document.documentElement.lang = this.currentLang;
    },
    init() {
        if (window.CURRENT_LANG && window.CURRENT_LANG !== this.currentLang) {
            this.currentLang = window.CURRENT_LANG;
            localStorage.setItem("linia_lang", window.CURRENT_LANG);
        } else if (!this.SUPPORTED_LANGS.includes(this.currentLang)) {
            this.currentLang = 'fr';
            localStorage.setItem('linia_lang', 'fr');
        }
        this.addSwitcher();
        this.translatePage();
    },
    addSwitcher() {
        document.addEventListener('click', (e) => {
            const btn = e.target.closest('.lang-switcher-btn');
            if (btn) {
                e.preventDefault();
                e.stopPropagation();
                this.toggleMenu(btn);
                return;
            }
            if (!e.target.closest('.lang-menu')) {
                this.closeMenu();
            }
        }, true);
    },
    toggleMenu(btn) {
        let menu = document.getElementById('langMenu');
        let overlay = document.getElementById('langOverlay');
        if (menu) {
            this.closeMenu();
            return;
        }
        overlay = document.createElement('div');
        overlay.id = 'langOverlay';
        overlay.className = 'lang-modal-overlay';
        overlay.onclick = () => this.closeMenu();
        document.body.appendChild(overlay);
        menu = document.createElement('div');
        menu.id = 'langMenu';
        menu.className = 'lang-menu lang-modal';
        this.SUPPORTED_LANGS.forEach(lang => {
            const option = document.createElement('button');
            option.className = `lang-option ${lang === this.currentLang ? 'active' : ''}`;
            option.innerHTML = `<span>${lang.toUpperCase()}</span>`;
            option.onclick = (e) => {
                e.stopPropagation();
                this.setLang(lang);
                this.closeMenu();
            };
            menu.appendChild(option);
        });
        document.body.appendChild(menu);
        requestAnimationFrame(() => {
            overlay.classList.add('show');
            menu.classList.add('show');
        });
    },
    closeMenu() {
        const menu = document.getElementById('langMenu');
        const overlay = document.getElementById('langOverlay');
        if (menu) menu.classList.remove('show');
        if (overlay) overlay.classList.remove('show');
        setTimeout(() => {
            if (menu) menu.remove();
            if (overlay) overlay.remove();
        }, 300);
    }
};
document.addEventListener('DOMContentLoaded', () => i18n.init());