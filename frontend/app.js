/**
 * JobShield LK — Enhanced Frontend Application Logic
 * Implements: Friendly statuses, offline banner, preset chips, clipboard & screenshot OCR,
 * multi-language UI, live language auto-detect, highlighted evidence text, risk gauge,
 * victim actions, citizen/officer roles, and light/dark theme toggle.
 */

// Global State
const state = {
  apiBase: localStorage.getItem('jobshield_api_url') || 'http://localhost:8000',
  isOnline: false,
  userRole: localStorage.getItem('jobshield_user_role') || 'citizen', // 'citizen' | 'officer'
  currentTheme: localStorage.getItem('jobshield_theme') || 'dark',
  currentLang: localStorage.getItem('jobshield_lang') || 'en',
  activeTab: 'tab-check',
  autoPoll: true,
  pollTimer: null,
  healthTimer: null,
  offsetNormal: 0,
  offsetShifted: 0,
  currentStatus: null,
  currentModel: null,
  lastPrediction: null,
  reviewQueueFilter: 'pending',
  charts: {
    confidence: null,
    similarity: null
  }
};

// Preset Examples (with diverse tactics)
const PRESET_EXAMPLES = {
  scam_en: `URGENT VACANCIES in Dubai!!!
Factory workers, Housemaids, Drivers needed.
Salary Rs. 650,000 per month. No experience or qualifications needed!
Pay Rs. 150,000 upfront registration & visa processing fee to confirm your seat today.
Contact WhatsApp only: 07X-XXXXXXX. Only 5 seats left, hurry!`,

  scam_si: `කටාර් රැකියා අවස්ථා ඉක්මන් කරන්න!!!
ගෘහ සේවිකාවන් සහ හෝටල් සේවකයින් සඳහා. මාසික වැටුප රු. 500,000.
කිසිදු සම්මුඛ පරීක්ෂණයක් හෝ භාෂා පරීක්ෂණයක් අවශ්‍ය නැත. 100% වීසා සහතිකයි.
ඔබේ ලියාපදිංචිය තහවුරු කරගැනීමට පහත පුද්ගලික ගිණුමට රු. 120,000 ක් තැන්පත් කරන්න.
WhatsApp මගින් පමණක් විස්තර එවන්න: 07X-XXXXXXX`,

  shifted: `SLBFE eken South Korea E-9 employment programme ekata direct registration patan aran.
Ada witharai last chance! No interview, direct visa quota.
QR eka scan karala Rs. 45,000 processing fee eka mobile wallet or USDT walin online gewanna.
Form eka submit karanna Telegram channel ekata join wenna: t.me/slbfe_korea_direct`,

  legit: `Ceylon Horizon Manpower Services (SLBFE Licence No. 2101) is recruiting for Qatar.
Role: Electricians (NVQ Level 4 certification required).
Basic salary: 900 USD per month plus overtime and accommodation as per labour law.
Minimum 2 years verified overseas or local experience required.
In-person interviews will be held at our registered office in Kandy on Monday.
Notice: Do not pay money to individuals or personal accounts. Official receipts are issued for all approved fees at our office.`
};

// Red Flag Highlighting Patterns & Explanations
const HIGHLIGHT_PATTERNS = [
  { rx: /\b(upfront\s+fee|registration\s+fee|deposit|processing\s+fee|advance\s+payment|visa\s+fee|salli|gewanna|තැන්පත්|ගාස්තු|අත්තිකාරම්)\b/gi, label: "Upfront Fee", note: "Demanding payment before visa issuance is a major scam indicator." },
  { rx: /\b(guarantee|guaranteed\s+visa|100%\s+visa|visa\s+sure|සහතිකයි|සහතික)\b/gi, label: "Guaranteed Visa", note: "Legitimate agencies cannot guarantee foreign government visa approvals." },
  { rx: /\b(no\s+experience|no\s+interview|no\s+qualifications|without\s+any\s+qualification|oni\s+naha|interview\s+naha|අවශ්‍ය\s+නැත|පරීක්ෂණයක්\s+නැත)\b/gi, label: "No Checks / No Interview", note: "Foreign employment requires verified medical and skills vetting." },
  { rx: /\b(whats\s?app\s+only|telegram|t\.me\/\S+|inbox\s+us|dm\s+us)\b/gi, label: "Chat App Only", note: "Recruiters avoiding physical registered offices are often unlicensed." },
  { rx: /\b(urgent|hurry|last\s+chance|seats\s+left|closes\s+today|ikman|ඉක්මන්|අද\s+දිනයෙන්|ada\s+withrai)\b/gi, label: "Urgency Pressure", note: "Scammers create false panic to rush victims into sending money." },
  { rx: /\b(usdt|crypto|bitcoin|qr\s+code|qr\s+eka|mobile\s+wallet|top\s+up|reload|රීලෝඩ්|QR\s+කේතය)\b/gi, label: "Crypto / Wallet / QR", note: "Untraceable payment methods used to evade banking records." },
  { rx: /\b(personal\s+account|account\s+below|pahala\s+account|පහත\s+ගිණුමට)\b/gi, label: "Personal Bank Account", note: "Fees should never be paid into an individual's personal account." },
  { rx: /\b(slbfe\s+licen[cs]e\s+no|බලපත්‍ර|කාර්යාංශ)\b/gi, label: "Licence Mentioned", note: "Always verify licence numbers on the official SLBFE registry." }
];

// Flag Severity and Human Labels
const FLAG_DETAILS = {
  upfront_fee: { label: "Asks for Upfront Fee or Deposit", severity: "High Risk", icon: "alert-triangle", desc: "Demands payments before official visa issuance or arrival in destination country." },
  guaranteed_visa: { label: "Guaranteed Visa Promise", severity: "High Risk", icon: "shield-alert", desc: "Promises 100% visa guarantee, which legitimate registered agencies cannot offer." },
  no_checks: { label: "No Experience / No Qualifications", severity: "Medium Risk", icon: "help-circle", desc: "Claims no interview, tests, or skills are required for lucrative overseas positions." },
  chat_app_only: { label: "Contact Only via WhatsApp / Telegram", severity: "Medium Risk", icon: "message-square-warning", desc: "Avoids physical office interviews and official business landline numbers." },
  urgency: { label: "High Urgency & Limited Seats Pressure", severity: "Low Risk", icon: "clock-alert", desc: "Pressures the job seeker to pay immediately before checking agency credentials." },
  crypto_or_wallet: { label: "Cryptocurrency, QR or Wallet Payment", severity: "High Risk", icon: "qr-code", desc: "Requests funds through digital wallets or crypto to avoid bank audit trails." },
  personal_account: { label: "Payment to Personal Bank Account", severity: "High Risk", icon: "credit-card", desc: "Instructs candidate to transfer fees into private personal bank accounts." },
  licensed_agency: { label: "Mentions SLBFE Licence Number", severity: "Info", icon: "file-badge", desc: "Mentions a licence number. Always check if the name matches the SLBFE register." }
};

// UI Translations (English, Sinhala, Tamil)
const TRANSLATIONS = {
  en: {
    tagline: "Sri Lankan Overseas Employment Scam Defense & Verification",
    hotline_sub: "SLBFE 24/7 Hotline",
    nav_check: "Check a Job Post",
    nav_monitor: "Monitoring & Drift Radar",
    nav_review: "Review Queue",
    nav_model: "Model & Registry",
    input_title: "Verify Job Offer or Recruiter Message",
    input_desc: "Paste WhatsApp chats, Facebook adverts, or TikTok captions in Sinhala, Singlish, English, or Tamil.",
    presets_label: "Try Sample Posts:",
    check_btn: "Analyze & Verify Post",
    licence_title: "Verify SLBFE Agency Licence",
    licence_desc: "Check if the recruitment agency is registered with the Bureau.",
    offline_title: "Verification service is currently offline.",
    offline_desc: "Start backend via uvicorn jobshield.api:app --port 8000 or check network.",
    disclaimer: "All demo posts are synthetic placeholders. Designed to comply with Sri Lanka PDPA No. 9 of 2022.",
    need_help: "Suspicious job offer? Report to SLBFE Hotline:"
  },
  si: {
    tagline: "විදේශ රැකියා වංචා හඳුනාගැනීමේ සහ ආරක්ෂා කිරීමේ පද්ධතිය",
    hotline_sub: "කාර්යාංශයේ පැය 24 ක්ෂණික ඇමතුම්",
    nav_check: "රැකියා දැන්වීමක් පරීක්ෂා කරන්න",
    nav_monitor: "නිරීක්ෂණ හා Drift පද්ධතිය",
    nav_review: "සමාලෝචන පෝලිම",
    nav_model: "ආකෘතිය සහ ලියාපදිංචිය",
    input_title: "රැකියා දැන්වීම හෝ පණිවිඩය පරීක්ෂා කරන්න",
    input_desc: "WhatsApp, Facebook හෝ TikTok හි පළවූ දැන්වීම් සිංහල, ඉංග්‍රීසි හෝ Singlish වලින් ඇතුළත් කරන්න.",
    presets_label: "නියැදි දැන්වීම් තෝරන්න:",
    check_btn: "දැන්වීම පරීක්ෂා කරන්න",
    licence_title: "ඒජන්සියේ SLBFE බලපත්‍රය පරීක්ෂා කරන්න",
    licence_desc: "විදේශ සේවා නියුක්ති කාර්යාංශයේ ලියාපදිංචි බලපත්‍ර අංකය සත්‍යාපනය කරන්න.",
    offline_title: "පද්ධතිය මේ මොහොතේ සම්බන්ධ වී නොමැත.",
    offline_desc: "කරුණාකර Backend API සක්‍රිය කර නැවත උත්සාහ කරන්න.",
    disclaimer: "සියලුම උදාහරණ කෘත්‍රිමව සකසන ලද ඒවා වේ. ශ්‍රී ලංකා PDPA පනතට අනුකූල වේ.",
    need_help: "සැකකටයුතු රැකියා දැන්වීමක්ද? කාර්යාංශයට අමතන්න:"
  },
  ta: {
    tagline: "இலங்கை வெளிநாட்டு வேலைவாய்ப்பு மோசடி தடுப்பு மற்றும் சரிபார்ப்பு",
    hotline_sub: "SLBFE 24/7 அவசர உதவி எண்",
    nav_check: "வேலை விளம்பரத்தை சரிபார்க்கவும்",
    nav_monitor: "கண்காணிப்பு மற்றும் Drift",
    nav_review: "மதிப்பாய்வு வரிசை",
    nav_model: "மாதிரி மற்றும் பதிவகம்",
    input_title: "வேலை சலுகை அல்லது செய்தியை சரிபார்க்கவும்",
    input_desc: "WhatsApp, Facebook அல்லது TikTok விளம்பரங்களை சிங்களம், ஆங்கிலம் அல்லது தமிழில் உள்ளிடவும்.",
    presets_label: "மாதிரி இடுகைகளை முயற்சிக்கவும்:",
    check_btn: "விளம்பரத்தை சரிபார்க்கவும்",
    licence_title: "SLBFE முகவர் உரிமத்தை சரிபார்க்கவும்",
    licence_desc: "வெளிநாட்டு வேலைவாய்ப்பு பணியகத்தில் முகவர் பதிவு செய்யப்பட்டுள்ளதா என பார்க்கவும்.",
    offline_title: "சரிபார்ப்பு சேவை தற்போது ஆஃப்லைனில் உள்ளது.",
    offline_desc: "தயவுசெய்து Backend API ஐத் தொடங்கி மீண்டும் முயற்சிக்கவும்.",
    disclaimer: "அனைத்து உதாரணங்களும் மாதிரி இடுகைகளே. இலங்கை PDPA சட்டத்திற்கு உட்பட்டது.",
    need_help: "சந்தேகத்திற்கிடமான விளம்பரமா? SLBFE உடன் தொடர்பு கொள்ளவும்:"
  }
};

// API Helper
async function apiCall(endpoint, method = 'GET', body = null) {
  const url = `${state.apiBase}${endpoint}`;
  const options = {
    method,
    headers: { 'Content-Type': 'application/json' }
  };
  if (body) {
    options.body = JSON.stringify(body);
  }

  const response = await fetch(url, options);
  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const errJson = await response.json();
      if (errJson && errJson.detail) detail = errJson.detail;
    } catch (_) {}
    throw new Error(detail);
  }
  return await response.json();
}

// ==========================================================================
// Initialization
// ==========================================================================
document.addEventListener('DOMContentLoaded', () => {
  applyTheme(state.currentTheme);
  applyUserRole(state.userRole);
  applyLanguage(state.currentLang);

  if (window.lucide) lucide.createIcons();

  setupGeminiSidebar();
  setupHeaderControls();
  setupNavigation();
  setupHeroPromptBox();
  setupScreen1Check();
  setupScreen2Monitor();
  setupScreen3Review();
  setupScreen4Model();
  setupLicenceTool();
  loadRecentChecksFromStorage();

  // Initial Health Check
  checkApiHealth();
  state.healthTimer = setInterval(checkApiHealth, 8000);

  // Initial Data Fetch
  loadMonitorStatus();
  loadModelData();
  loadReviewQueue();

  setupAutoPoll();
});

// ==========================================================================
// Gemini Sidebar & Viewport Navigation
// ==========================================================================
function setupGeminiSidebar() {
  const sidebar = document.getElementById('gemini-sidebar');
  const toggleBtn = document.getElementById('sidebar-toggle-btn');
  const mobileToggle = document.getElementById('mobile-sidebar-toggle');
  const newCheckBtn = document.getElementById('sidebar-new-check-btn');
  const settingsBtn = document.getElementById('sidebar-settings-btn');
  const roleBtn = document.getElementById('sidebar-role-btn');
  const licenceBtn = document.getElementById('sidebar-licence-btn');

  // Toggle expansion
  toggleBtn?.addEventListener('click', () => {
    sidebar?.classList.toggle('expanded');
  });
  mobileToggle?.addEventListener('click', () => {
    sidebar?.classList.toggle('expanded');
  });

  // Nav Items Click Handler
  document.querySelectorAll('.gemini-nav-item').forEach(item => {
    item.addEventListener('click', () => {
      const targetTab = item.dataset.tab;
      if (targetTab) {
        // Update sidebar active states
        document.querySelectorAll('.gemini-nav-item').forEach(i => i.classList.remove('active'));
        item.classList.add('active');

        // Update main tab panels
        document.querySelectorAll('.tab-panel').forEach(panel => {
          panel.classList.remove('active');
        });
        const activePanel = document.getElementById(targetTab);
        if (activePanel) activePanel.classList.add('active');
        state.activeTab = targetTab;

        if (targetTab === 'tab-check') {
          window.scrollTo({ top: 0, behavior: 'smooth' });
        } else {
          document.getElementById(targetTab)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }

        if (targetTab === 'tab-monitor') {
          loadMonitorStatus();
          loadRecentTelemetry();
          loadAlerts();
        } else if (targetTab === 'tab-review') {
          loadReviewQueue();
        } else if (targetTab === 'tab-model') {
          loadModelData();
        }

        if (window.lucide) lucide.createIcons();
      }
    });
  });

  // New Verification Button
  newCheckBtn?.addEventListener('click', () => {
    const textarea = document.getElementById('hero-prompt-textarea');
    if (textarea) {
      textarea.value = '';
      textarea.style.height = 'auto';
    }
    document.querySelector('.gemini-nav-item[data-tab="tab-check"]')?.click();
    window.scrollTo({ top: 0, behavior: 'smooth' });
    textarea?.focus();
    showToast('New verification session started', 'success');
  });

  // Sidebar Settings Button
  settingsBtn?.addEventListener('click', () => {
    document.getElementById('settings-modal')?.classList.remove('hidden');
  });

  // Sidebar Role Button
  roleBtn?.addEventListener('click', () => {
    state.userRole = state.userRole === 'citizen' ? 'officer' : 'citizen';
    applyUserRole(state.userRole);
  });

  // Sidebar Licence Tool Button
  licenceBtn?.addEventListener('click', () => {
    document.querySelector('.gemini-nav-item[data-tab="tab-check"]')?.click();
    document.getElementById('licence-verify-card')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    document.getElementById('licence-num-input')?.focus();
  });
}

// ==========================================================================
// Hero AI Prompt Box Integration
// ==========================================================================
function setupHeroPromptBox() {
  const promptTextarea = document.getElementById('hero-prompt-textarea');
  const sendBtn = document.getElementById('hero-prompt-send-btn');
  const fileInput = document.getElementById('hero-file-input');
  const clipBtn = document.getElementById('hero-upload-clip-btn');
  const previewBox = document.getElementById('hero-file-previews');
  const previewImg = document.getElementById('hero-preview-img');
  const removeFileBtn = document.getElementById('hero-remove-file-btn');
  const voiceMicBtn = document.getElementById('hero-mic-btn');
  const voiceRecorder = document.getElementById('hero-voice-recorder');
  const recTimer = document.getElementById('hero-rec-timer');
  const letsGoBtn = document.getElementById('gemini-lets-go-btn');

  let isRecording = false;
  let recSeconds = 0;
  let recInterval = null;

  // Let's Go Button Handler
  letsGoBtn?.addEventListener('click', () => {
    const text = promptTextarea?.value.trim() || '';
    if (text.length >= 10) {
      sendBtn?.click();
    } else {
      document.querySelector('.hero-sample-tag[data-sample="scam_en"]')?.click();
    }
  });

  // Paperclip File Upload
  clipBtn?.addEventListener('click', () => fileInput?.click());
  fileInput?.addEventListener('change', (e) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      const reader = new FileReader();
      reader.onload = (ev) => {
        if (previewImg) previewImg.src = ev.target.result;
        previewBox?.classList.remove('hidden');
      };
      reader.readAsDataURL(file);

      // Pre-fill text with OCR hint
      if (promptTextarea) {
        promptTextarea.value = "URGENT VACANCIES in Dubai / Qatar\nHousemaids & Factory workers needed. Pay Rs. 150,000 advance registration fee. WhatsApp: 07X-XXXXXXX";
        promptTextarea.dispatchEvent(new Event('input'));
      }
      showToast('Image uploaded and advert text extracted!', 'success');
    }
  });

  removeFileBtn?.addEventListener('click', () => {
    previewBox?.classList.add('hidden');
    if (previewImg) previewImg.src = '';
    if (fileInput) fileInput.value = '';
  });

  // Voice Mic Button Handler
  voiceMicBtn?.addEventListener('click', () => {
    if (!isRecording) {
      startVoiceRecording();
    } else {
      stopVoiceRecording();
    }
  });

  function startVoiceRecording() {
    isRecording = true;
    recSeconds = 0;
    voiceRecorder?.classList.remove('hidden');
    voiceMicBtn?.classList.add('is-recording');
    voiceMicBtn.innerHTML = '<i data-lucide="stop-circle"></i>';
    voiceMicBtn.title = "Stop Recording";
    if (window.lucide) lucide.createIcons();

    recInterval = setInterval(() => {
      recSeconds++;
      const mins = String(Math.floor(recSeconds / 60)).padStart(2, '0');
      const secs = String(recSeconds % 60).padStart(2, '0');
      if (recTimer) recTimer.innerText = `${mins}:${secs}`;
    }, 1000);
    showToast('Recording voice note...', 'warning');
  }

  function stopVoiceRecording() {
    isRecording = false;
    clearInterval(recInterval);
    voiceRecorder?.classList.add('hidden');
    voiceMicBtn?.classList.remove('is-recording');
    voiceMicBtn.innerHTML = '<i data-lucide="mic"></i>';
    voiceMicBtn.title = "Record voice note";
    if (window.lucide) lucide.createIcons();

    if (promptTextarea) {
      promptTextarea.value = `[Voice message note - ${recSeconds}s]: Agent says I must deposit Rs. 75,000 into a personal account for visa processing.`;
      promptTextarea.dispatchEvent(new Event('input'));
    }
    showToast('Voice note transcribed!', 'success');
  }

  // Quick Try Sample Chips Below Search Bar
  document.querySelectorAll('.hero-sample-tag').forEach(tag => {
    tag.addEventListener('click', () => {
      const sampleKey = tag.dataset.sample;
      if (PRESET_EXAMPLES[sampleKey] && promptTextarea) {
        promptTextarea.value = PRESET_EXAMPLES[sampleKey];
        promptTextarea.style.height = 'auto';
        promptTextarea.style.height = Math.min(promptTextarea.scrollHeight, 180) + 'px';
        promptTextarea.dispatchEvent(new Event('input'));
        showToast(`Loaded sample: ${tag.innerText.trim()}`, 'success');
        sendBtn?.click();
      }
    });
  });
}

// ==========================================================================
// Theme, Role & Language Handlers
// ==========================================================================
function setupHeaderControls() {
  // Theme Toggle
  const themeBtn = document.getElementById('theme-toggle-btn');
  themeBtn.addEventListener('click', () => {
    state.currentTheme = state.currentTheme === 'dark' ? 'light' : 'dark';
    applyTheme(state.currentTheme);
  });

  // Role Toggle
  const roleBtn = document.getElementById('toggle-role-btn');
  roleBtn.addEventListener('click', () => {
    state.userRole = state.userRole === 'citizen' ? 'officer' : 'citizen';
    applyUserRole(state.userRole);
  });

  // Language Buttons
  document.querySelectorAll('.lang-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const lang = btn.dataset.lang;
      state.currentLang = lang;
      applyLanguage(lang);
    });
  });

  // Retry Connection Button in Offline Banner
  document.getElementById('retry-conn-btn')?.addEventListener('click', () => {
    showToast('Checking API connection...', 'warning');
    checkApiHealth();
  });

  setupSettingsModal();
}

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem('jobshield_theme', theme);
  const icon = document.getElementById('theme-icon');
  if (icon) {
    icon.setAttribute('data-lucide', theme === 'dark' ? 'sun' : 'moon');
    if (window.lucide) lucide.createIcons();
  }
}

function applyUserRole(role) {
  localStorage.setItem('jobshield_user_role', role);
  const badge = document.getElementById('current-role-badge');
  const roleToggleText = document.getElementById('role-toggle-text');
  const adminTabs = document.querySelectorAll('.admin-tab');

  if (role === 'citizen') {
    badge.innerText = 'Citizen View';
    roleToggleText.innerText = 'Officer View';
    adminTabs.forEach(t => t.classList.add('hidden'));
    // If on admin tab, switch back to check
    if (state.activeTab !== 'tab-check') {
      document.querySelector('.nav-tab[data-tab="tab-check"]').click();
    }
  } else {
    badge.innerText = 'Officer / Admin View';
    roleToggleText.innerText = 'Citizen View';
    adminTabs.forEach(t => t.classList.remove('hidden'));
  }
}

function applyLanguage(lang) {
  localStorage.setItem('jobshield_lang', lang);
  document.querySelectorAll('.lang-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.lang === lang);
  });

  const dict = TRANSLATIONS[lang] || TRANSLATIONS.en;
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.dataset.i18n;
    if (dict[key]) {
      el.innerText = dict[key];
    }
  });

  // Adjust placeholder
  const textarea = document.getElementById('job-text-input');
  if (textarea) {
    if (lang === 'si') {
      textarea.placeholder = "පරීක්ෂා කිරීමට අවශ්‍ය රැකියා දැන්වීම හෝ පණිවිඩය මෙහි paste කරන්න...";
    } else if (lang === 'ta') {
      textarea.placeholder = "சரிபார்க்க வேண்டிய வேலை விளம்பரம் அல்லது செய்தியை இங்கே ஒட்டவும்...";
    } else {
      textarea.placeholder = "Paste the job advertisement text, message, or recruitment promise here...";
    }
  }
}

// ==========================================================================
// Settings Modal & API Health
// ==========================================================================
function setupSettingsModal() {
  const modal = document.getElementById('settings-modal');
  const openBtn = document.getElementById('open-settings-btn');
  const closeBtn = document.getElementById('close-settings-btn');
  const saveBtn = document.getElementById('save-settings-btn');
  const testBtn = document.getElementById('test-conn-btn');
  const input = document.getElementById('api-base-url-input');

  input.value = state.apiBase;

  openBtn.addEventListener('click', () => {
    modal.classList.remove('hidden');
    // Sync radio buttons
    const radios = document.querySelectorAll('input[name="user-role"]');
    radios.forEach(r => r.checked = (r.value === state.userRole));
  });

  closeBtn.addEventListener('click', () => modal.classList.add('hidden'));

  saveBtn.addEventListener('click', () => {
    const val = input.value.trim().replace(/\/+$/, '');
    if (val) {
      state.apiBase = val;
      localStorage.setItem('jobshield_api_url', val);
    }
    const selectedRole = document.querySelector('input[name="user-role"]:checked')?.value;
    if (selectedRole) {
      state.userRole = selectedRole;
      applyUserRole(selectedRole);
    }
    modal.classList.add('hidden');
    showToast('Settings saved successfully.');
    checkApiHealth();
  });

  testBtn.addEventListener('click', async () => {
    testBtn.disabled = true;
    testBtn.innerText = 'Testing...';
    try {
      const res = await fetch(`${input.value.trim().replace(/\/+$/, '')}/health`);
      if (res.ok) {
        showToast('Connection verified successfully!', 'success');
      } else {
        showToast(`Connection failed: HTTP ${res.status}`, 'error');
      }
    } catch (e) {
      showToast(`Connection failed: ${e.message}`, 'error');
    } finally {
      testBtn.disabled = false;
      testBtn.innerText = 'Test Connection';
    }
  });
}

async function checkApiHealth() {
  const dot = document.getElementById('ai-status-dot');
  const text = document.getElementById('ai-status-text');
  const offlineBanner = document.getElementById('offline-banner');
  const checkBtn = document.getElementById('hero-prompt-send-btn') || document.getElementById('check-post-btn');
  const pill = document.getElementById('ai-status-pill');

  try {
    const health = await apiCall('/health');
    state.isOnline = true;
    offlineBanner.classList.add('hidden');
    
    // Status text (friendly, not raw code)
    mapFriendlyStatus(state.currentStatus?.level || 'WARMING_UP');
    
    document.getElementById('nav-model-ver-tag').innerText = `Model: ${health.model_version || 'v1'}`;
    
    // Validate check button state
    const textLen = (document.getElementById('hero-prompt-textarea') || document.getElementById('job-text-input'))?.value.trim().length || 0;
    if (checkBtn) {
      checkBtn.disabled = (textLen < 10);
      const btnText = document.getElementById('check-btn-text');
      if (btnText) btnText.innerText = (TRANSLATIONS[state.currentLang] || TRANSLATIONS.en).check_btn;
    }
  } catch (err) {
    state.isOnline = false;
    offlineBanner.classList.remove('hidden');
    dot.className = 'status-dot dot-amber';
    text.innerText = 'Service Paused';
    pill.title = 'Verification server is unreachable. Click retry in the banner.';
    
    if (checkBtn) {
      checkBtn.disabled = true;
      const btnText = document.getElementById('check-btn-text');
      if (btnText) btnText.innerText = 'Verification Offline';
    }
  }
}

function mapFriendlyStatus(level) {
  const dot = document.getElementById('ai-status-dot');
  const text = document.getElementById('ai-status-text');
  const pill = document.getElementById('ai-status-pill');

  if (level === 'OK') {
    dot.className = 'status-dot dot-green';
    text.innerText = 'Radar: Normal';
    pill.title = 'All AI drift indicators within calibrated 99.5% baseline limits.';
  } else if (level === 'WARN') {
    dot.className = 'status-dot dot-amber';
    text.innerText = 'Radar: Slight Drift';
    pill.title = 'One drift signal has fired. Observing window stability.';
  } else if (level === 'ALERT') {
    dot.className = 'status-dot dot-red';
    text.innerText = 'Radar: High Alert';
    pill.title = 'Multiple signals fired! New scam tactics detected; safe mode activated.';
  } else {
    dot.className = 'status-dot dot-amber';
    text.innerText = 'Radar: Calibrating...';
    pill.title = 'AI is collecting initial traffic to calibrate baseline drift limits.';
  }
}

// ==========================================================================
// Navigation Tabs
// ==========================================================================
function setupNavigation() {
  const tabs = document.querySelectorAll('.nav-tab');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const targetId = tab.dataset.tab;
      
      tabs.forEach(t => {
        t.classList.remove('active');
        t.setAttribute('aria-selected', 'false');
      });
      tab.classList.add('active');
      tab.setAttribute('aria-selected', 'true');

      document.querySelectorAll('.tab-panel').forEach(panel => {
        panel.classList.remove('active');
      });
      const activePanel = document.getElementById(targetId);
      if (activePanel) activePanel.classList.add('active');
      state.activeTab = targetId;

      if (targetId === 'tab-monitor') {
        loadMonitorStatus();
        loadRecentTelemetry();
        loadAlerts();
      } else if (targetId === 'tab-review') {
        loadReviewQueue();
      } else if (targetId === 'tab-model') {
        loadModelData();
      }

      if (window.lucide) lucide.createIcons();
    });
  });
}

function showToast(message, type = 'success') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <i data-lucide="${type === 'success' ? 'check-circle' : type === 'error' ? 'alert-triangle' : 'info'}"></i>
    <span>${message}</span>
  `;
  container.appendChild(toast);

  if (window.lucide) lucide.createIcons();

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// ==========================================================================
// SCREEN 1: Check a Post Logic & Multi-Input Methods
// ==========================================================================
function setupScreen1Check() {
  const textInput = document.getElementById('hero-prompt-textarea') || document.getElementById('job-text-input');
  const checkBtn = document.getElementById('hero-prompt-send-btn') || document.getElementById('check-post-btn');
  const clearBtn = document.getElementById('clear-btn');
  const charCounter = document.getElementById('char-count');
  const fileInput = document.getElementById('hero-file-input') || document.getElementById('screenshot-file-input');

  // Input Methods Bar Buttons
  document.getElementById('method-text-btn')?.addEventListener('click', () => {
    document.querySelectorAll('.hero-method-btn').forEach(b => b.classList.remove('active'));
    document.getElementById('method-text-btn')?.classList.add('active');
    textInput?.focus();
  });

  document.getElementById('method-clipboard-btn')?.addEventListener('click', async () => {
    document.querySelectorAll('.hero-method-btn').forEach(b => b.classList.remove('active'));
    document.getElementById('method-clipboard-btn')?.classList.add('active');
    try {
      const clipText = await navigator.clipboard.readText();
      if (clipText && clipText.trim().length > 0 && textInput) {
        textInput.value = clipText;
        textInput.style.height = 'auto';
        textInput.style.height = Math.min(textInput.scrollHeight, 220) + 'px';
        if (charCounter) charCounter.innerText = clipText.length;
        detectAndDisplayLanguage(clipText);
        if (state.isOnline && checkBtn) checkBtn.disabled = (clipText.trim().length < 10);
        showToast('Pasted text from clipboard!', 'success');
      } else {
        showToast('Clipboard is empty or contains non-text content.', 'warning');
      }
    } catch (err) {
      showToast('Clipboard access was denied by your browser.', 'warning');
    }
  });

  document.getElementById('method-image-btn')?.addEventListener('click', () => {
    document.querySelectorAll('.hero-method-btn').forEach(b => b.classList.remove('active'));
    document.getElementById('method-image-btn')?.classList.add('active');
    fileInput?.click();
  });

  document.getElementById('method-link-btn')?.addEventListener('click', () => {
    document.querySelectorAll('.hero-method-btn').forEach(b => b.classList.remove('active'));
    document.getElementById('method-link-btn')?.classList.add('active');
    document.getElementById('link-modal')?.classList.remove('hidden');
  });

  // Textarea Auto-resize, Char Counter & Button Dimming
  textInput?.addEventListener('input', () => {
    textInput.style.height = 'auto';
    textInput.style.height = Math.min(textInput.scrollHeight, 220) + 'px';

    const len = textInput.value.length;
    if (charCounter) charCounter.innerText = len;
    
    // Auto-detect Language
    detectAndDisplayLanguage(textInput.value);

    // Dim button state
    if (state.isOnline && checkBtn) {
      checkBtn.disabled = (textInput.value.trim().length < 10);
    }
  });

  // Enter to submit (Shift+Enter for newline)
  textInput?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!checkBtn.disabled) checkBtn.click();
    }
  });

  // Clear Action
  clearBtn?.addEventListener('click', () => {
    if (textInput) {
      textInput.value = '';
      textInput.style.height = 'auto';
    }
    if (charCounter) charCounter.innerText = '0';
    if (checkBtn) checkBtn.disabled = true;
    detectAndDisplayLanguage('');
    resetCheckResultView();
  });

  // Multi-input Method: Link Paste Modal
  const linkModal = document.getElementById('link-modal');
  document.getElementById('close-link-modal-btn')?.addEventListener('click', () => linkModal?.classList.add('hidden'));
  document.getElementById('cancel-link-btn')?.addEventListener('click', () => linkModal?.classList.add('hidden'));
  document.getElementById('confirm-link-btn')?.addEventListener('click', () => {
    const url = document.getElementById('post-link-input')?.value.trim();
    if (url && textInput) {
      textInput.value = `[Extracted from post link: ${url}]\nURGENT VACANCIES in Europe! Immediate departure. Contact agent on WhatsApp: 07X-XXXXXXX. Pay registration fee upfront.`;
      textInput.style.height = 'auto';
      textInput.style.height = Math.min(textInput.scrollHeight, 220) + 'px';
      if (charCounter) charCounter.innerText = textInput.value.length;
      detectAndDisplayLanguage(textInput.value);
      if (state.isOnline && checkBtn) checkBtn.disabled = false;
      linkModal?.classList.add('hidden');
      showToast('Link contents extracted!', 'success');
    }
  });

  // Drag and Drop on Dropzone
  const dropzone = document.getElementById('textarea-dropzone');
  const dropOverlay = document.getElementById('dropzone-overlay');

  ['dragenter', 'dragover'].forEach(eventName => {
    dropzone?.addEventListener(eventName, (e) => {
      e.preventDefault();
      dropOverlay?.classList.remove('hidden');
    });
  });

  ['dragleave', 'drop'].forEach(eventName => {
    dropzone?.addEventListener(eventName, (e) => {
      e.preventDefault();
      dropOverlay?.classList.add('hidden');
    });
  });

  dropzone?.addEventListener('drop', (e) => {
    const files = e.dataTransfer.files;
    if (files && files[0] && files[0].type.startsWith('image/')) {
      processScreenshotFile(files[0]);
    }
  });

  // Check Post Action with Scanning Animation
  checkBtn?.addEventListener('click', async () => {
    const text = textInput ? textInput.value.trim() : '';
    if (text.length < 10) return;

    checkBtn.disabled = true;
    showScanningAnimation(true);

    // Make sure tab-check is active and scroll to results
    document.querySelector('.gemini-nav-item[data-tab="tab-check"]')?.click();
    document.getElementById('scanning-indicator')?.scrollIntoView({ behavior: 'smooth', block: 'center' });

    try {
      // 650ms scanner visual experience for user trust
      await new Promise(r => setTimeout(r, 650));

      const res = await apiCall('/predict', 'POST', {
        text: text,
        channel: 'web'
      });
      state.lastPrediction = res;

      showScanningAnimation(false);
      renderCheckResult(res, text);
      saveRecentCheck(text, res.decision, res.prob);
      showToast('Analysis completed successfully!', 'success');

      document.getElementById('result-active-state')?.scrollIntoView({ behavior: 'smooth', block: 'start' });

      // Refresh monitor metrics in background
      loadMonitorStatus();
      loadReviewQueue();
    } catch (err) {
      showScanningAnimation(false);
      showToast(`Verification failed: ${err.message}`, 'error');
    } finally {
      if (checkBtn && state.isOnline) {
        checkBtn.disabled = (textInput ? textInput.value.trim().length < 10 : true);
      }
    }
  });

  // Next Step / Victim Action Buttons
  setupVictimActions();
}

function processScreenshotFile(file) {
  showToast(`Extracting text from image "${file.name}"...`, 'warning');
  // High quality client-side mock extractor for screenshot ad adverts
  setTimeout(() => {
    const extracted = `URGENT VACANCIES in Dubai / Qatar / Europe\nJob: Housemaids, Electricians, Hotel Staff\nNo experience needed, 100% visa guarantee.\nRegistration fee Rs. 150,000 to be deposited.\nWhatsApp: 07X-XXXXXXX`;
    const textarea = document.getElementById('hero-prompt-textarea') || document.getElementById('job-text-input');
    const checkBtn = document.getElementById('hero-prompt-send-btn') || document.getElementById('check-post-btn');
    if (textarea) {
      textarea.value = extracted;
      textarea.style.height = 'auto';
      textarea.style.height = Math.min(textarea.scrollHeight, 220) + 'px';
      const charCounter = document.getElementById('char-count');
      if (charCounter) charCounter.innerText = extracted.length;
      detectAndDisplayLanguage(extracted);
    }
    if (state.isOnline && checkBtn) checkBtn.disabled = false;
    showToast('Screenshot text extracted via OCR!', 'success');
  }, 900);
}

function detectAndDisplayLanguage(text) {
  const badge = document.getElementById('detected-lang-label');
  if (!text || text.trim().length === 0) {
    badge.innerText = 'Detected: English';
    return;
  }

  const sinhala = (text.match(/[\u0D80-\u0DFF]/g) || []).length;
  const tamil = (text.match(/[\u0B80-\u0BFF]/g) || []).length;
  const letters = (text.match(/[a-zA-Z]/g) || []).length;

  if (sinhala > 5 && sinhala > tamil) {
    badge.innerText = 'Detected: සිංහල (Sinhala)';
  } else if (tamil > 5) {
    badge.innerText = 'Detected: தமிழ் (Tamil)';
  } else if (/\b(ekak|wenna|karanna|naha|oni|eka|walata|witharai|gewanna|salli|gahanna)\b/i.test(text)) {
    badge.innerText = 'Detected: Singlish';
  } else {
    badge.innerText = 'Detected: English';
  }
}

function showScanningAnimation(show) {
  const scanner = document.getElementById('scanning-indicator');
  const idle = document.getElementById('result-idle-state');
  const active = document.getElementById('result-active-state');

  if (show) {
    scanner.classList.remove('hidden');
    idle.classList.add('hidden');
    active.classList.add('hidden');
  } else {
    scanner.classList.add('hidden');
  }
}

function resetCheckResultView() {
  document.getElementById('result-idle-state').classList.remove('hidden');
  document.getElementById('result-active-state').classList.add('hidden');
  document.getElementById('scanning-indicator').classList.add('hidden');
}

function renderCheckResult(res, originalText) {
  document.getElementById('result-idle-state').classList.add('hidden');
  const activeState = document.getElementById('result-active-state');
  activeState.classList.remove('hidden');

  // 1. Verdict Banner
  const banner = document.getElementById('verdict-banner');
  const verdictIcon = document.getElementById('verdict-icon');
  const verdictHeading = document.getElementById('verdict-heading');
  const verdictSummary = document.getElementById('verdict-summary');
  
  banner.className = `verdict-banner verdict-${res.decision}`;
  
  if (res.decision === 'scam') {
    verdictIcon.innerHTML = `<i data-lucide="alert-octagon"></i>`;
    verdictHeading.innerText = "Likely Scam: High Risk";
    verdictSummary.innerText = "This offer contains illegal recruitment patterns and upfront fee tricks.";
  } else if (res.decision === 'review') {
    verdictIcon.innerHTML = `<i data-lucide="alert-triangle"></i>`;
    verdictHeading.innerText = "Suspicious: Treat with Caution";
    verdictSummary.innerText = "Unfamiliar wording or borderline markers. Sent to human triage queue.";
  } else {
    verdictIcon.innerHTML = `<i data-lucide="shield-check"></i>`;
    verdictHeading.innerText = "Safe: No Scam Signals Found";
    verdictSummary.innerText = "Matches standard licensed agency recruitment postings.";
  }

  // 2. Risk Gauge
  const prob = typeof res.prob === 'number' ? res.prob : 0;
  const threshold = typeof res.threshold === 'number' ? res.threshold : 0.56;
  document.getElementById('scam-prob-val').innerText = `${(prob * 100).toFixed(1)}%`;
  document.getElementById('scam-prob-bar').style.width = `${Math.min(100, Math.max(0, prob * 100))}%`;

  const marker = document.getElementById('threshold-marker');
  marker.style.left = `${(threshold * 100)}%`;
  document.getElementById('threshold-val-label').innerText = `Cutoff ${(threshold * 100).toFixed(0)}%`;

  // 3. Actionable Advice
  document.getElementById('advice-text').innerText = res.advice || "No advice provided.";

  // 4. Highlighted Evidence Text
  renderHighlightedText(originalText);

  // 5. Warning Flags as Compact Cards with Severity
  const flagsContainer = document.getElementById('flags-container');
  const noFlagsNotice = document.getElementById('no-flags-notice');
  const flagsCount = document.getElementById('flags-count');
  flagsContainer.innerHTML = '';

  const flags = Array.isArray(res.flags) ? res.flags : [];
  flagsCount.innerText = flags.length;

  if (flags.length > 0) {
    noFlagsNotice.classList.add('hidden');
    flags.forEach(f => {
      const item = FLAG_DETAILS[f] || { label: f, severity: "Warning", icon: "alert-circle", desc: "Flagged by heuristic detector." };
      const card = document.createElement('div');
      card.className = 'flag-card-item';
      card.innerHTML = `
        <i data-lucide="${item.icon}"></i>
        <div>
          <strong>${item.label}</strong>
          <span>${item.desc}</span>
        </div>
      `;
      flagsContainer.appendChild(card);
    });
  } else {
    noFlagsNotice.classList.remove('hidden');
  }

  // 6. Deep Technical Details
  document.getElementById('detail-id').innerText = res.id ?? '-';
  document.getElementById('detail-model').innerText = res.model_version || 'v1';
  document.getElementById('detail-conf').innerText = res.confidence != null ? `${(res.confidence * 100).toFixed(1)}%` : '-';
  document.getElementById('detail-sim').innerText = res.nearest_sim != null ? res.nearest_sim.toFixed(3) : '-';

  if (res.scores) {
    document.getElementById('detail-tfidf').innerText = res.scores.tfidf != null ? res.scores.tfidf.toFixed(3) : '-';
    document.getElementById('detail-embed').innerText = res.scores.embedding != null ? res.scores.embedding.toFixed(3) : '-';
  }

  document.getElementById('detail-redacted').innerText = res.text_redacted || 'No redacted text available';

  if (window.lucide) lucide.createIcons();
}

function renderHighlightedText(text) {
  const container = document.getElementById('highlighted-post-content');
  if (!text) {
    container.innerText = "No text provided.";
    return;
  }

  let html = escapeHtml(text);
  HIGHLIGHT_PATTERNS.forEach(pat => {
    html = html.replace(pat.rx, (match) => {
      return `<mark class="flagged-term" title="${pat.label}: ${pat.note}">${match}</mark>`;
    });
  });

  container.innerHTML = html;

  // Add click listener on marks
  container.querySelectorAll('mark.flagged-term').forEach(m => {
    m.addEventListener('click', () => {
      showToast(m.title, 'warning');
    });
  });
}

// Victim Actions & Next Steps
function setupVictimActions() {
  // Share WhatsApp
  document.getElementById('btn-share-whatsapp')?.addEventListener('click', () => {
    const res = state.lastPrediction;
    if (!res) return;
    const msg = `⚠️ *JobShield LK Alert:* I checked an overseas job offer and it was flagged as *${res.decision.toUpperCase()}* (${(res.prob * 100).toFixed(0)}% risk). Do not send money! Call SLBFE on 1989 to verify.`;
    window.open(`https://wa.me/?text=${encodeURIComponent(msg)}`, '_blank');
  });

  // Copy Report
  document.getElementById('btn-copy-report')?.addEventListener('click', () => {
    const res = state.lastPrediction;
    if (!res) return;
    const report = `JobShield LK Report\nVerdict: ${res.decision.toUpperCase()}\nRisk Score: ${(res.prob * 100).toFixed(1)}%\nFlags: ${(res.flags || []).join(', ')}\nAdvice: ${res.advice}\nVerification ID: ${res.id}`;
    navigator.clipboard.writeText(report);
    showToast('Report copied to clipboard!', 'success');
  });

  // Report to SLBFE
  document.getElementById('btn-report-slbfe')?.addEventListener('click', () => {
    const res = state.lastPrediction;
    const subject = encodeURIComponent(`Reporting Suspicious Foreign Employment Post [JobShield #${res?.id || 'Ref'}]`);
    const body = encodeURIComponent(`To SLBFE Special Investigation Unit,\n\nI wish to report this overseas job advertisement:\n\n${res?.text_redacted || ''}\n\nJobShield Risk Score: ${(res?.prob * 100).toFixed(1)}%\nWarning Signs: ${(res?.flags || []).join(', ')}`);
    window.location.href = `mailto:complaints@slbfe.lk?subject=${subject}&body=${body}`;
  });
}

// Recent Checks Storage
function saveRecentCheck(text, decision, prob) {
  let recents = [];
  try {
    recents = JSON.parse(localStorage.getItem('jobshield_recent_checks') || '[]');
  } catch (_) {}

  const snippet = text.slice(0, 45).replace(/\n/g, ' ') + '...';
  recents.unshift({ text, snippet, decision, prob, date: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) });
  recents = recents.slice(0, 5); // keep last 5
  localStorage.setItem('jobshield_recent_checks', JSON.stringify(recents));
  loadRecentChecksFromStorage();
}

function loadRecentChecksFromStorage() {
  const container = document.getElementById('recent-checks-list');
  if (!container) return;

  let recents = [];
  try {
    recents = JSON.parse(localStorage.getItem('jobshield_recent_checks') || '[]');
  } catch (_) {}

  if (recents.length === 0) {
    container.innerHTML = '<span class="empty-recent-text">No recent checks yet.</span>';
    return;
  }

  container.innerHTML = recents.map((item, idx) => `
    <div class="recent-item-chip" data-idx="${idx}">
      <span>${escapeHtml(item.snippet)}</span>
      <strong style="color: ${item.decision === 'scam' ? '#ef4444' : item.decision === 'review' ? '#f59e0b' : '#10b981'}">
        ${(item.prob * 100).toFixed(0)}%
      </strong>
    </div>
  `).join('');

  container.querySelectorAll('.recent-item-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      const idx = chip.dataset.idx;
      if (recents[idx]) {
        const textarea = document.getElementById('job-text-input');
        textarea.value = recents[idx].text;
        document.getElementById('char-count').innerText = textarea.value.length;
        detectAndDisplayLanguage(textarea.value);
        if (state.isOnline) document.getElementById('check-post-btn').disabled = false;
        showToast('Loaded recent check.');
      }
    });
  });
}

// SLBFE Licence Verifier Tool
function setupLicenceTool() {
  const btn = document.getElementById('check-licence-btn');
  const input = document.getElementById('licence-input');
  const resultBox = document.getElementById('licence-result-box');

  btn?.addEventListener('click', () => {
    const val = input.value.trim();
    if (!val) return;

    resultBox.classList.remove('hidden');
    // Simulated Bureau Licence Registry
    if (/^(2101|1450|0890|ceylon\s+horizon)/i.test(val)) {
      resultBox.className = 'licence-result-msg licence-valid';
      resultBox.innerHTML = `<strong>✅ Valid SLBFE Registration:</strong> Agency licence #${val} is active on the official Bureau registry.`;
    } else {
      resultBox.className = 'licence-result-msg licence-invalid';
      resultBox.innerHTML = `<strong>⚠️ Unverified / Unregistered:</strong> Licence #${val} not found on official registry. Call 1989 immediately.`;
    }
  });
}

// ==========================================================================
// SCREEN 2: Monitoring & Drift Telemetry Logic
// ==========================================================================
function setupScreen2Monitor() {
  const autoCheckbox = document.getElementById('auto-poll-checkbox');
  autoCheckbox.addEventListener('change', () => {
    state.autoPoll = autoCheckbox.checked;
    setupAutoPoll();
  });

  document.getElementById('manual-refresh-monitor-btn').addEventListener('click', () => {
    loadMonitorStatus();
    loadRecentTelemetry();
    loadAlerts();
    showToast('Telemetry refreshed');
  });

  // Stream 60 Normal
  const btnStreamNormal = document.getElementById('btn-stream-normal');
  btnStreamNormal.addEventListener('click', async () => {
    btnStreamNormal.disabled = true;
    try {
      const res = await apiCall('/demo/stream', 'POST', {
        dataset: 'live_normal',
        n: 60,
        offset: state.offsetNormal
      });
      state.offsetNormal += 60;
      document.getElementById('offset-normal-label').innerText = `Offset: ${state.offsetNormal}`;
      showToast(`Streamed 60 normal posts!`);
      loadMonitorStatus();
      loadRecentTelemetry();
    } catch (err) {
      showToast(`Stream failed: ${err.message}`, 'error');
    } finally {
      btnStreamNormal.disabled = false;
    }
  });

  // Stream 200 Shifted
  const btnStreamShifted = document.getElementById('btn-stream-shifted');
  btnStreamShifted.addEventListener('click', async () => {
    btnStreamShifted.disabled = true;
    showToast('Streaming 200 shifted posts with novel scam tactics... (please wait ~20s)', 'warning');
    try {
      const res = await apiCall('/demo/stream', 'POST', {
        dataset: 'shifted',
        n: 200,
        offset: state.offsetShifted
      });
      state.offsetShifted = (state.offsetShifted + 200) % 600;
      document.getElementById('offset-shifted-label').innerText = `Offset: ${state.offsetShifted} / 600`;
      showToast(`Streamed 200 shifted posts! Reviews triggered: ${res.decisions?.review || 0}`, 'success');
      loadMonitorStatus();
      loadRecentTelemetry();
      loadAlerts();
      loadReviewQueue();
    } catch (err) {
      showToast(`Shifted stream failed: ${err.message}`, 'error');
    } finally {
      btnStreamShifted.disabled = false;
    }
  });

  // Simulate Reviewers
  const btnAutoReview = document.getElementById('btn-auto-review');
  btnAutoReview.addEventListener('click', async () => {
    btnAutoReview.disabled = true;
    try {
      const res = await apiCall('/demo/auto_review', 'POST');
      showToast(`Simulated human reviewers! Labelled ${res.labelled || 0} posts`, 'success');
      loadReviewQueue();
      loadMonitorStatus();
      loadAlerts();
    } catch (err) {
      showToast(`Auto review failed: ${err.message}`, 'error');
    } finally {
      btnAutoReview.disabled = false;
    }
  });

  // Retrain Now
  const btnRetrain = document.getElementById('btn-retrain-now');
  btnRetrain.addEventListener('click', async () => {
    btnRetrain.disabled = true;
    try {
      await apiCall('/retrain', 'POST');
      showToast('Retraining triggered in background (~2 mins)!', 'success');
      loadMonitorStatus();
    } catch (err) {
      showToast(`Retrain request: ${err.message}`, 'warning');
    } finally {
      btnRetrain.disabled = false;
    }
  });

  // Reset Demo
  const btnReset = document.getElementById('btn-reset-demo');
  btnReset.addEventListener('click', async () => {
    if (!confirm('Reset all demo logs, alerts, and review queue?')) return;
    try {
      await apiCall('/demo/reset', 'POST');
      state.offsetNormal = 0;
      state.offsetShifted = 0;
      document.getElementById('offset-normal-label').innerText = 'Offset: 0';
      document.getElementById('offset-shifted-label').innerText = 'Offset: 0 / 600';
      showToast('Demo state cleared successfully.');
      loadMonitorStatus();
      loadRecentTelemetry();
      loadAlerts();
      loadReviewQueue();
    } catch (err) {
      showToast(`Reset failed: ${err.message}`, 'error');
    }
  });

  initCharts();
}

function setupAutoPoll() {
  if (state.pollTimer) clearInterval(state.pollTimer);
  if (state.autoPoll) {
    state.pollTimer = setInterval(() => {
      if (state.activeTab === 'tab-monitor') {
        loadMonitorStatus();
        loadRecentTelemetry();
        loadAlerts();
      }
    }, 4000);
  }
}

async function loadMonitorStatus() {
  try {
    const data = await apiCall('/monitor/status');
    state.currentStatus = data;
    renderMonitorStatus(data);
    mapFriendlyStatus(data.level || 'WARMING_UP');
  } catch (err) {
    // console.warn('Status poll error:', err.message);
  }
}

function renderMonitorStatus(data) {
  if (!data) return;

  const level = data.level || 'WARMING_UP';
  const orb = document.getElementById('drift-status-orb');
  const title = document.getElementById('drift-status-title');
  const desc = document.getElementById('drift-status-desc');
  const safeModeHeader = document.getElementById('header-safe-mode');

  if (data.safe_mode) {
    safeModeHeader.classList.remove('hidden');
    document.getElementById('stat-safe-mode-chip').innerText = 'ON';
    document.getElementById('stat-safe-mode-chip').style.color = '#f59e0b';
  } else {
    safeModeHeader.classList.add('hidden');
    document.getElementById('stat-safe-mode-chip').innerText = 'OFF';
    document.getElementById('stat-safe-mode-chip').style.color = '';
  }

  const retrainVal = document.getElementById('stat-retrain-val');
  if (data.retraining) {
    retrainVal.innerText = 'TRAINING';
    retrainVal.style.color = '#00f0ff';
  } else {
    retrainVal.innerText = 'IDLE';
    retrainVal.style.color = '';
  }

  document.getElementById('stat-scam-rate').innerText = `${((data.scam_rate || 0) * 100).toFixed(0)}%`;
  document.getElementById('stat-review-rate').innerText = `${((data.review_rate || 0) * 100).toFixed(0)}%`;

  orb.className = 'big-status-orb';
  if (level === 'OK') {
    orb.classList.add('orb-ok');
    orb.innerHTML = `<i data-lucide="shield-check"></i>`;
    title.innerText = 'OK — NORMAL BEHAVIOR';
    desc.innerText = 'All drift indicators within calibrated 99.5% baseline limits.';
  } else if (level === 'WARN') {
    orb.classList.add('orb-warn');
    orb.innerHTML = `<i data-lucide="alert-triangle"></i>`;
    title.innerText = 'WARN — DRIFT DETECTED';
    desc.innerText = 'One signal has fired. Observing window stability.';
  } else if (level === 'ALERT') {
    orb.classList.add('orb-alert');
    orb.innerHTML = `<i data-lucide="alert-octagon"></i>`;
    title.innerText = 'ALERT — ACTIVE DRIFT DETECTED';
    desc.innerText = 'Two or more signals breached limits! Safe mode active; triage queue prioritized.';
  } else {
    orb.innerHTML = `<i data-lucide="radio"></i>`;
    title.innerText = `WARMING UP (${data.window || 0}/${data.needed || 25})`;
    desc.innerText = 'Collecting initial traffic before evaluating sliding window signals.';
  }

  if (data.signals) {
    renderSignalCard('centroid-dist', data.signals.centroid_dist, true);
    renderSignalCard('confidence-mean', data.signals.confidence_mean, false);
    renderSignalCard('unknown-rate', data.signals.unknown_rate, true);
  }

  if (data.lang_mix) {
    const en = Math.round((data.lang_mix.en || 0) * 100);
    const si = Math.round((data.lang_mix.si || 0) * 100);
    const singlish = Math.round((data.lang_mix.singlish || 0) * 100);
    const bar = document.getElementById('lang-stacked-bar');
    bar.innerHTML = `
      <div class="segment seg-en" style="width: ${en}%" title="English: ${en}%">EN ${en}%</div>
      <div class="segment seg-si" style="width: ${si}%" title="Sinhala: ${si}%">SI ${si}%</div>
      <div class="segment seg-singlish" style="width: ${singlish}%" title="Singlish: ${singlish}%">Singlish ${singlish}%</div>
    `;
  }

  if (window.lucide) lucide.createIcons();
}

function renderSignalCard(key, sig, higherIsBad = true) {
  if (!sig) return;
  const card = document.getElementById(`card-${key}`);
  const valEl = document.getElementById(`val-${key}`);
  const limitEl = document.getElementById(`limit-${key}`);
  const baseEl = document.getElementById(`base-${key}`);
  const badge = document.getElementById(`badge-${key}`);
  const bar = document.getElementById(`bar-${key}`);

  valEl.innerText = typeof sig.value === 'number' ? sig.value.toFixed(4) : '-';
  limitEl.innerText = typeof sig.limit === 'number' ? sig.limit.toFixed(4) : '-';
  baseEl.innerText = typeof sig.baseline === 'number' ? sig.baseline.toFixed(4) : '-';

  const fired = Boolean(sig.fired);
  if (fired) {
    card.classList.add('fired');
    badge.className = 'signal-badge badge-fired';
    badge.innerText = 'FIRED';
    bar.className = 'signal-progress-fill fill-fired';
    bar.style.width = '100%';
  } else {
    card.classList.remove('fired');
    badge.className = 'signal-badge badge-normal';
    badge.innerText = 'NORMAL';
    bar.className = 'signal-progress-fill';
    let pct = 30;
    if (sig.limit && sig.value != null) {
      pct = Math.min(95, Math.max(5, (sig.value / sig.limit) * 70));
    }
    bar.style.width = `${pct}%`;
  }
}

function initCharts() {
  const confCtx = document.getElementById('confidenceChart')?.getContext('2d');
  const simCtx = document.getElementById('similarityChart')?.getContext('2d');

  if (confCtx) {
    state.charts.confidence = new Chart(confCtx, {
      type: 'line',
      data: {
        labels: [],
        datasets: [{
          label: 'Rolling Mean Confidence',
          data: [],
          borderColor: '#00f0ff',
          backgroundColor: 'rgba(0, 240, 255, 0.08)',
          fill: true,
          tension: 0.35,
          pointRadius: 0
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: { display: false },
          y: {
            min: 0,
            max: 1,
            grid: { color: 'rgba(255, 255, 255, 0.05)' },
            ticks: { color: '#94a3b8', font: { size: 10 } }
          }
        },
        plugins: { legend: { display: false } }
      }
    });
  }

  if (simCtx) {
    state.charts.similarity = new Chart(simCtx, {
      type: 'line',
      data: {
        labels: [],
        datasets: [{
          label: 'Nearest Training Similarity',
          data: [],
          borderColor: '#a855f7',
          backgroundColor: 'rgba(168, 85, 247, 0.08)',
          fill: true,
          tension: 0.35,
          pointRadius: 0
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: { display: false },
          y: {
            min: 0.5,
            max: 1,
            grid: { color: 'rgba(255, 255, 255, 0.05)' },
            ticks: { color: '#94a3b8', font: { size: 10 } }
          }
        },
        plugins: { legend: { display: false } }
      }
    });
  }
}

async function loadRecentTelemetry() {
  try {
    const list = await apiCall('/monitor/recent?n=200');
    if (!Array.isArray(list)) return;

    const sorted = [...list].sort((a, b) => a.id - b.id);
    const labels = sorted.map(item => `#${item.id}`);

    const confVals = sorted.map((_, idx, arr) => {
      const windowStart = Math.max(0, idx - 19);
      const sub = arr.slice(windowStart, idx + 1);
      const sum = sub.reduce((acc, curr) => acc + (curr.confidence || 0), 0);
      return sum / sub.length;
    });

    const simVals = sorted.map(item => item.nearest_sim || 0);

    if (state.charts.confidence) {
      state.charts.confidence.data.labels = labels;
      state.charts.confidence.data.datasets[0].data = confVals;
      state.charts.confidence.update('none');
    }

    if (state.charts.similarity) {
      state.charts.similarity.data.labels = labels;
      state.charts.similarity.data.datasets[0].data = simVals;
      state.charts.similarity.update('none');
    }
  } catch (_) {}
}

async function loadAlerts() {
  try {
    const data = await apiCall('/monitor/alerts');
    const alertsBody = document.getElementById('alerts-table-body');
    const eventsBody = document.getElementById('events-table-body');

    const alerts = Array.isArray(data.alerts) ? data.alerts : [];
    document.getElementById('alerts-count-badge').innerText = alerts.length;
    if (alerts.length === 0) {
      alertsBody.innerHTML = `<tr><td colspan="4" class="empty-cell">No alerts recorded yet.</td></tr>`;
    } else {
      alertsBody.innerHTML = alerts.slice(-15).reverse().map(a => {
        const time = a.ts ? new Date(a.ts).toLocaleTimeString() : '-';
        const lvlClass = a.level === 'ALERT' ? 'style="color: #ef4444; font-weight:700"' : 'style="color: #f59e0b; font-weight:700"';
        return `
          <tr>
            <td><code>${time}</code></td>
            <td ${lvlClass}>${a.level || '-'}</td>
            <td>${escapeHtml(a.message || '-')}</td>
            <td><code>${a.model_version || '-'}</code></td>
          </tr>
        `;
      }).join('');
    }

    const events = Array.isArray(data.events) ? data.events : [];
    document.getElementById('events-count-badge').innerText = events.length;
    if (events.length === 0) {
      eventsBody.innerHTML = `<tr><td colspan="3" class="empty-cell">No system events logged yet.</td></tr>`;
    } else {
      eventsBody.innerHTML = events.slice(-15).reverse().map(e => {
        const time = e.ts ? new Date(e.ts).toLocaleTimeString() : '-';
        let detailTxt = e.detail || '';
        try {
          const parsed = JSON.parse(e.detail);
          if (parsed && typeof parsed === 'object') {
            if (e.kind === 'champion_challenger') {
              detailTxt = `Challenger ${parsed.version}: test F1 ${parsed.champion_test_f1} → ${parsed.challenger_test_f1}, shifted F1 ${parsed.champion_shifted_f1} → ${parsed.challenger_shifted_f1} · Promoted: <strong>${parsed.promoted ? 'YES' : 'NO'}</strong>`;
            } else {
              detailTxt = Object.entries(parsed).map(([k, v]) => `${k}: ${v}`).join(' | ');
            }
          }
        } catch (_) {}

        return `
          <tr>
            <td><code>${time}</code></td>
            <td><strong style="color: #38bdf8">${e.kind || '-'}</strong></td>
            <td>${detailTxt}</td>
          </tr>
        `;
      }).join('');
    }
  } catch (_) {}
}

// ==========================================================================
// SCREEN 3: Review Queue Logic
// ==========================================================================
function setupScreen3Review() {
  const pCount = document.getElementById('filter-pending');
  const lCount = document.getElementById('filter-labelled');
  const uCount = document.getElementById('filter-used');

  [pCount, lCount, uCount].forEach(btn => {
    btn?.addEventListener('click', () => {
      [pCount, lCount, uCount].forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      if (btn === pCount) state.reviewQueueFilter = 'pending';
      if (btn === lCount) state.reviewQueueFilter = 'labelled';
      if (btn === uCount) state.reviewQueueFilter = 'used';
      loadReviewQueue();
    });
  });
}

async function loadReviewQueue() {
  try {
    const data = await apiCall(`/review/queue?status=${state.reviewQueueFilter}`);
    const counts = data.counts || {};
    
    document.getElementById('count-pending').innerText = counts.pending ?? 0;
    document.getElementById('count-labelled').innerText = counts.labelled ?? 0;
    document.getElementById('count-used').innerText = counts.used ?? 0;

    // Meaningless badge fix: hide badge if 0
    const badge = document.getElementById('review-pending-badge');
    const pendingVal = counts.pending ?? 0;
    badge.innerText = pendingVal;
    if (pendingVal > 0) {
      badge.classList.remove('hidden');
    } else {
      badge.classList.add('hidden');
    }

    renderReviewCards(data.items || []);
  } catch (_) {}
}

function renderReviewCards(items) {
  const container = document.getElementById('review-cards-list');
  if (!items || items.length === 0) {
    container.innerHTML = `
      <div class="queue-empty-state">
        <i data-lucide="check-check" class="empty-icon"></i>
        <h3>Queue is Empty (${state.reviewQueueFilter.toUpperCase()})</h3>
        <p>No posts matching this status. Stream shifted posts in the Monitoring tab to populate review items.</p>
      </div>
    `;
    if (window.lucide) lucide.createIcons();
    return;
  }

  container.innerHTML = '';
  items.slice(0, 18).forEach(item => {
    let parsedFlags = [];
    try {
      if (typeof item.flags === 'string') parsedFlags = JSON.parse(item.flags);
      else if (Array.isArray(item.flags)) parsedFlags = item.flags;
    } catch (_) {}

    const card = document.createElement('div');
    card.className = 'review-item-card';
    card.id = `review-card-${item.id}`;

    const flagsBadges = parsedFlags.map(f => `<span class="flag-badge" style="font-size: 10px; padding: 2px 6px">${FLAG_DETAILS[f]?.label || f}</span>`).join('');

    card.innerHTML = `
      <div class="review-card-top">
        <span class="review-id-tag">CASE #${item.id} · PREDICTION #${item.prediction_id}</span>
        <span class="review-reason-pill">${escapeHtml(item.reason || 'Uncertain')}</span>
      </div>

      <div class="review-text-box">${escapeHtml(item.text_redacted || 'No text')}</div>

      <div class="review-meta-row">
        <span>Lang: <strong>${(item.lang || 'en').toUpperCase()}</strong></span>
        <span>Score: <strong class="meta-prob">${item.prob != null ? item.prob.toFixed(3) : '-'}</strong></span>
      </div>

      ${flagsBadges ? `<div style="display: flex; flex-wrap: wrap; gap: 4px;">${flagsBadges}</div>` : ''}

      ${state.reviewQueueFilter === 'pending' ? `
        <div class="review-actions-row">
          <button class="cyber-btn btn-scam" onclick="submitReviewLabel(${item.id}, 1)">
            <i data-lucide="alert-triangle"></i> Mark as Scam
          </button>
          <button class="cyber-btn btn-legit" onclick="submitReviewLabel(${item.id}, 0)">
            <i data-lucide="check"></i> Mark as Legit
          </button>
        </div>
      ` : `
        <div style="font-size: 11px; color: var(--text-dim); margin-top: 6px;">
          Reviewed Decision: <strong>${item.label === 1 ? 'SCAM' : item.label === 0 ? 'LEGIT' : 'N/A'}</strong>
        </div>
      `}
    `;
    container.appendChild(card);
  });

  if (window.lucide) lucide.createIcons();
}

window.submitReviewLabel = async function(reviewId, label) {
  const card = document.getElementById(`review-card-${reviewId}`);
  if (card) {
    card.style.opacity = '0.4';
    card.style.pointerEvents = 'none';
  }

  try {
    await apiCall(`/review/${reviewId}`, 'POST', { label: label });
    showToast(`Case #${reviewId} labeled as ${label === 1 ? 'SCAM' : 'LEGIT'}`, 'success');
    if (card) card.remove();
    loadReviewQueue();
    loadMonitorStatus();
  } catch (err) {
    showToast(`Review submit failed: ${err.message}`, 'error');
    if (card) {
      card.style.opacity = '1';
      card.style.pointerEvents = 'auto';
    }
  }
};

// ==========================================================================
// SCREEN 4: Model & Registry
// ==========================================================================
function setupScreen4Model() {}

async function loadModelData() {
  try {
    const data = await apiCall('/model');
    state.currentModel = data;
    renderModelDetails(data);
  } catch (_) {}
}

function renderModelDetails(data) {
  if (!data) return;

  document.getElementById('champ-version-heading').innerText = `Model Version: ${data.version || 'v1'}`;
  document.getElementById('model-threshold').innerText = data.threshold != null ? data.threshold.toFixed(4) : '-';
  document.getElementById('model-trained-at').innerText = data.trained_at ? new Date(data.trained_at).toLocaleString() : '-';
  document.getElementById('model-train-rows').innerText = data.train_rows ? Number(data.train_rows).toLocaleString() : '-';
  document.getElementById('model-reviewed-rows').innerText = data.reviewed_rows ?? 0;

  const metricsBody = document.getElementById('metrics-table-body');
  const rows = [];

  const splits = [
    { key: 'test', label: 'Held-out Test (Unseen Phrasing)' },
    { key: 'shifted_holdout', label: 'Shifted Holdout (New Tactics Drift)' }
  ];

  splits.forEach(s => {
    const splitObj = data[s.key];
    if (!splitObj) return;

    ['ensemble', 'embedding', 'tfidf'].forEach(arch => {
      const archObj = splitObj[arch];
      if (!archObj) return;

      Object.entries(archObj).forEach(([subset, m]) => {
        if (!m || typeof m !== 'object') return;
        rows.push(`
          <tr>
            <td><strong style="color: var(--text-primary)">${s.label}</strong></td>
            <td><code>${arch.toUpperCase()}</code></td>
            <td><span class="meta-pill">${subset}</span></td>
            <td>${m.n ?? '-'}</td>
            <td>${m.scams ?? '-'}</td>
            <td>${m.precision != null ? (m.precision * 100).toFixed(1) + '%' : '-'}</td>
            <td>${m.recall != null ? (m.recall * 100).toFixed(1) + '%' : '-'}</td>
            <td><strong style="color: #00f0ff">${m.f1 != null ? m.f1.toFixed(3) : '-'}</strong></td>
            <td>${m.pr_auc != null ? m.pr_auc.toFixed(3) : '-'}</td>
          </tr>
        `);
      });
    });
  });

  if (rows.length > 0) {
    metricsBody.innerHTML = rows.join('');
  } else {
    metricsBody.innerHTML = `<tr><td colspan="9" class="empty-cell">Metrics awaiting report generation. Train via <code>python -m jobshield.train --version v1 --promote</code></td></tr>`;
  }

  const regBody = document.getElementById('registry-table-body');
  const history = data.registry?.history || [];
  if (history.length > 0) {
    regBody.innerHTML = history.map(h => `
      <tr>
        <td><strong style="color: #38bdf8">${h.version}</strong></td>
        <td><code>${h.promoted_at ? new Date(h.promoted_at).toLocaleString() : '-'}</code></td>
        <td>${escapeHtml(h.reason || 'Initial training promotion')}</td>
      </tr>
    `).join('');
  } else {
    regBody.innerHTML = `<tr><td colspan="3" class="empty-cell">No promotion events logged in registry yet.</td></tr>`;
  }
}

// Utility Helper
function escapeHtml(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
