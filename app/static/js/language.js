/*
HEARTGAURD - Language System (Arabic/English + RTL Support)
Handles language toggle, translations, and RTL layout
*/

class LanguageManager {
    constructor() {
        this.currentLanguage = localStorage.getItem('language') || 'en';
        
        this.translations = {
            en: {
                // Navigation
                'back': '←',
                'splash_title': 'HEARTGAURD',
                'splash_subtitle': 'AI-Powered Heart Intelligence',
                
                // Intro Page
                'intro_title': 'Advanced Heart Monitoring',
                'intro_description': 'HEARTGAURD utilizes cutting-edge AI to monitor cardiac health in real-time. Our advanced algorithms analyze ECG patterns, detect arrhythmias, and identify potential risks before they become critical.',
                'feature_real_time': 'Real-Time Monitoring',
                'feature_real_time_desc': 'Live ECG analysis with instant alerts',
                'feature_ai_detection': 'AI Detection',
                'feature_ai_detection_desc': 'Advanced machine learning algorithms',
                'feature_predictive': 'Predictive Analytics',
                'feature_predictive_desc': 'Early risk identification',
                'intro_cta': 'Let\'s Start',
                
                // Model Page
                'model_title': 'AI Analysis Pipeline',
                'model_description': 'Our intelligent system processes ECG data through multiple stages of analysis',
                'step_ecg': 'ECG Input',
                'step_analysis': 'AI Analysis',
                'step_diagnosis': 'Diagnosis',
                'parameters_title': 'Key ECG Parameters',
                'param_st': 'ST Segment',
                'param_st_desc': 'Elevation or depression indicating ischemia',
                'param_qrs': 'QRS Duration',
                'param_qrs_desc': 'Measures ventricular depolarization',
                'param_qt': 'QT Interval',
                'param_qt_desc': 'Assesses repolarization duration',
                'param_arrhythmia': 'Arrhythmia',
                'param_arrhythmia_desc': 'Irregular heart rhythm detection',
                'param_ischemia': 'Ischemia',
                'param_ischemia_desc': 'Reduced blood flow to heart muscle',
                'model_cta': 'View Dashboard',
                
                // Dashboard
                'doctor_dashboard': 'Doctor Dashboard',
                'vital_signs': 'Vital Signs',
                'heart_rate': 'Heart Rate',
                'blood_pressure': 'Blood Pressure',
                'respiration': 'Respiration',
                'temperature': 'Temperature',
                'ecg_waveform': 'Live ECG Waveform',
                'ai_diagnosis': 'AI Diagnosis Summary',
                'risk_level': 'Risk Level',
                'risk_low': 'Low Risk',
                'risk_medium': 'Medium Risk',
                'risk_high': 'High Risk',
                'status_normal': 'Normal',
                'status_abnormal': 'Abnormal',
                'bpm': 'bpm',
                'mmhg': 'mmHg',
                'breaths': 'breaths/min',
                'celsius': '°C',
            },
            ar: {
                // Navigation
                'back': '→',
                'splash_title': 'حماية القلب',
                'splash_subtitle': 'ذكاء قلبي مدعوم بالذكاء الاصطناعي',
                
                // Intro Page
                'intro_title': 'مراقبة القلب المتقدمة',
                'intro_description': 'تستخدم حماية القلب أحدث تقنيات الذكاء الاصطناعي لمراقبة صحة القلب في الوقت الفعلي. تحلل خوارزمياتنا المتقدمة أنماط مخطط كهربية القلب وتكتشف عدم انتظام ضربات القلب وتحدد المخاطر المحتملة قبل أن تصبح حرجة.',
                'feature_real_time': 'المراقبة في الوقت الفعلي',
                'feature_real_time_desc': 'تحليل مخطط كهربية القلب المباشر مع تنبيهات فورية',
                'feature_ai_detection': 'كشف الذكاء الاصطناعي',
                'feature_ai_detection_desc': 'خوارزميات التعلم الآلي المتقدمة',
                'feature_predictive': 'التحليلات التنبؤية',
                'feature_predictive_desc': 'تحديد المخاطر المبكرة',
                'intro_cta': 'Let\'s Start',
                
                // Model Page
                'model_title': 'خط أنابيب تحليل الذكاء الاصطناعي',
                'model_description': 'يعالج نظامنا الذكي بيانات مخطط كهربية القلب من خلال مراحل تحليل متعددة',
                'step_ecg': 'مدخلات ECG',
                'step_analysis': 'تحليل الذكاء الاصطناعي',
                'step_diagnosis': 'التشخيص',
                'parameters_title': 'معاملات مخطط كهربية القلب الرئيسية',
                'param_st': 'القطعة ST',
                'param_st_desc': 'الارتفاع أو الانخفاض يشير إلى الإقفار',
                'param_qrs': 'مدة QRS',
                'param_qrs_desc': 'يقيس إزالة الاستقطاب البطيني',
                'param_qt': 'فترة QT',
                'param_qt_desc': 'يقيم مدة إعادة الاستقطاب',
                'param_arrhythmia': 'عدم انتظام الضربات',
                'param_arrhythmia_desc': 'كشف عدم انتظام ضربات القلب',
                'param_ischemia': 'الإقفار',
                'param_ischemia_desc': 'تدفق دم منخفض لعضلة القلب',
                'model_cta': 'عرض لوحة التحكم',
                
                // Dashboard
                'doctor_dashboard': 'لوحة تحكم الطبيب',
                'vital_signs': 'العلامات الحيوية',
                'heart_rate': 'معدل ضربات القلب',
                'blood_pressure': 'ضغط الدم',
                'respiration': 'التنفس',
                'temperature': 'درجة الحرارة',
                'ecg_waveform': 'موجة مخطط كهربية القلب المباشرة',
                'ai_diagnosis': 'ملخص التشخيص بالذكاء الاصطناعي',
                'risk_level': 'مستوى الخطر',
                'risk_low': 'خطر منخفض',
                'risk_medium': 'خطر متوسط',
                'risk_high': 'خطر مرتفع',
                'status_normal': 'عادي',
                'status_abnormal': 'غير طبيعي',
                'bpm': 'نبضة/دقيقة',
                'mmhg': 'ملم زئبق',
                'breaths': 'نفس/دقيقة',
                'celsius': '°م',
            }
        };
        
        this.init();
    }

    init() {
        this.applyLanguage(this.currentLanguage);
        
        // Add event listener to language toggle button
        const languageToggle = document.querySelector('.language-toggle');
        if (languageToggle) {
            languageToggle.addEventListener('click', () => this.toggleLanguage());
            this.updateLanguageIcon();
        }
    }

    toggleLanguage() {
        this.currentLanguage = this.currentLanguage === 'en' ? 'ar' : 'en';
        this.applyLanguage(this.currentLanguage);
        localStorage.setItem('language', this.currentLanguage);
        this.updateLanguageIcon();
    }

    applyLanguage(lang) {
        const body = document.body;
        
        // Apply RTL for Arabic
        if (lang === 'ar') {
            body.classList.add('rtl');
            body.setAttribute('lang', 'ar');
            document.documentElement.setAttribute('dir', 'rtl');
        } else {
            body.classList.remove('rtl');
            body.setAttribute('lang', 'en');
            document.documentElement.setAttribute('dir', 'ltr');
        }
        
        // Update all text elements
        this.updateAllText(lang);
    }

    updateAllText(lang) {
        const translationKeys = Object.keys(this.translations[lang]);
        
        translationKeys.forEach(key => {
            const elements = document.querySelectorAll(`[data-i18n="${key}"]`);
            elements.forEach(el => {
                el.textContent = this.translations[lang][key];
            });
        });
    }

    updateLanguageIcon() {
        const languageToggle = document.querySelector('.language-toggle');
        if (languageToggle) {
            if (this.currentLanguage === 'ar') {
                languageToggle.textContent = 'EN';
                languageToggle.title = 'Switch to English';
            } else {
                languageToggle.textContent = 'ع';
                languageToggle.title = 'Switch to Arabic';
            }
        }
    }

    getText(key) {
        return this.translations[this.currentLanguage][key] || key;
    }
}

// Initialize language manager when DOM is ready
let languageManager;
document.addEventListener('DOMContentLoaded', () => {
    languageManager = new LanguageManager();
});
