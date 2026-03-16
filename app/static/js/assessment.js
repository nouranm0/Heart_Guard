// ============================================
// ASSESSMENT PAGE - FUNCTIONALITY
// ============================================

class AssessmentManager {
    constructor() {
        this.currentStep = 1;
        this.assessmentData = {
            file: null,
            patient: {},
            vitals: {},
            symptoms: []
        };
        this.init();
    }

    init() {
        this.setupFileUpload();
        this.setupFormNavigation();
        this.setupNavigation();
    }

    // ============================================
    // FILE UPLOAD HANDLING
    // ============================================

    setupFileUpload() {
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');
        const filePreview = document.getElementById('filePreview');
        const nextBtn = document.getElementById('nextBtn');
        const removeFile = document.getElementById('removeFile');

        // Click to upload
        uploadArea.addEventListener('click', () => fileInput.click());

        // File input change
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                this.handleFileSelect(e.target.files[0], uploadArea, filePreview, nextBtn);
            }
        });

        // Drag and drop
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });

        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });

        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            if (e.dataTransfer.files.length > 0) {
                this.handleFileSelect(e.dataTransfer.files[0], uploadArea, filePreview, nextBtn);
            }
        });

        // Remove file
        if (removeFile) {
            removeFile.addEventListener('click', () => {
                fileInput.value = '';
                this.assessmentData.file = null;
                filePreview.style.display = 'none';
                uploadArea.style.display = 'block';
                nextBtn.disabled = true;
            });
        }
    }

    handleFileSelect(file, uploadArea, filePreview, nextBtn) {
        // Validate file
        const validFormats = ['csv', 'xml', 'dat', 'ecg'];
        const fileExt = file.name.split('.').pop().toLowerCase();
        const maxSize = 10 * 1024 * 1024; // 10MB

        if (!validFormats.includes(fileExt)) {
            this.showNotification('Invalid file format. Please upload csv, xml, dat, or ecg file.', 'error');
            return;
        }

        if (file.size > maxSize) {
            this.showNotification('File is too large. Maximum size is 10MB.', 'error');
            return;
        }

        // Store file data
        this.assessmentData.file = {
            name: file.name,
            size: (file.size / 1024 / 1024).toFixed(2),
            type: fileExt
        };

        // Update UI
        document.getElementById('fileName').textContent = file.name;
        document.getElementById('fileSize').textContent = `${this.assessmentData.file.size} MB`;

        uploadArea.style.display = 'none';
        filePreview.style.display = 'flex';
        nextBtn.disabled = false;

        this.showNotification('File uploaded successfully!', 'success');
    }

    // ============================================
    // FORM NAVIGATION
    // ============================================

    setupFormNavigation() {
        const nextBtn = document.getElementById('nextBtn');
        const cards = document.querySelectorAll('.assessment-card');
        const steps = document.querySelectorAll('.step');

        if (nextBtn) {
            nextBtn.addEventListener('click', () => {
                this.goToStep(2);
            });
        }

        // Back and Next buttons in forms
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('btn')) {
                const text = e.target.getAttribute('data-i18n') || e.target.textContent;

                if (text.includes('next') || text === 'Next') {
                    const currentCard = cards[this.currentStep - 1];
                    const form = currentCard.querySelector('form');
                    
                    if (form && !form.checkValidity()) {
                        form.reportValidity();
                        return;
                    }

                    this.saveCurrentStepData();
                    this.goToStep(this.currentStep + 1);
                } else if (text.includes('back') || text === 'Back') {
                    this.goToStep(this.currentStep - 1);
                } else if (text.includes('review') || text === 'Review') {
                    this.saveCurrentStepData();
                    this.goToStep(4);
                    this.updateReviewSection();
                } else if (text.includes('submit') || text === 'Submit Assessment') {
                    this.submitAssessment();
                }
            }
        });
    }

    saveCurrentStepData() {
        if (this.currentStep === 2) {
            const form = document.querySelectorAll('.assessment-card')[1].querySelector('form');
            if (form) {
                this.assessmentData.patient = {
                    name: form.elements[0].value,
                    age: form.elements[1].value,
                    gender: form.elements[2].value,
                    medicalHistory: form.elements[3].value
                };
            }
        } else if (this.currentStep === 3) {
            const form = document.querySelectorAll('.assessment-card')[2].querySelector('form');
            if (form) {
                const inputs = form.querySelectorAll('input');
                this.assessmentData.vitals = {
                    heartRate: inputs[0].value,
                    systolic: inputs[1].value,
                    diastolic: inputs[2].value,
                    temperature: inputs[3].value,
                    respiration: inputs[4].value,
                    o2Saturation: inputs[5].value
                };
            }
        }
    }

    goToStep(stepNumber) {
        if (stepNumber < 1 || stepNumber > 4) return;

        const cards = document.querySelectorAll('.assessment-card');
        const steps = document.querySelectorAll('.step');

        // Hide all cards
        cards.forEach(card => card.classList.remove('active-step'));

        // Show current card
        if (cards[stepNumber - 1]) {
            cards[stepNumber - 1].classList.add('active-step');
        }

        // Update step indicator
        steps.forEach((step, index) => {
            if (index < stepNumber) {
                step.classList.add('active');
            } else {
                step.classList.remove('active');
            }
        });

        this.currentStep = stepNumber;

        // Scroll to top
        document.querySelector('.assessment-content').scrollTop = 0;
    }

    updateReviewSection() {
        const reviewPatient = document.getElementById('reviewPatient');
        const reviewVitals = document.getElementById('reviewVitals');
        const reviewFile = document.getElementById('reviewFile');

        // Patient info
        if (reviewPatient && this.assessmentData.patient.name) {
            reviewPatient.innerHTML = `
                <p><strong>Name:</strong> <span>${this.assessmentData.patient.name}</span></p>
                <p><strong>Age:</strong> <span>${this.assessmentData.patient.age}</span></p>
                <p><strong>Gender:</strong> <span>${this.assessmentData.patient.gender}</span></p>
                <p><strong>Medical History:</strong> <span>${this.assessmentData.patient.medicalHistory || 'N/A'}</span></p>
            `;
        }

        // Vital signs
        if (reviewVitals && this.assessmentData.vitals.heartRate) {
            reviewVitals.innerHTML = `
                <p><strong>Heart Rate:</strong> <span>${this.assessmentData.vitals.heartRate} BPM</span></p>
                <p><strong>Blood Pressure:</strong> <span>${this.assessmentData.vitals.systolic}/${this.assessmentData.vitals.diastolic}</span></p>
                <p><strong>Temperature:</strong> <span>${this.assessmentData.vitals.temperature}°C</span></p>
                <p><strong>Respiration:</strong> <span>${this.assessmentData.vitals.respiration}</span></p>
                <p><strong>O2 Saturation:</strong> <span>${this.assessmentData.vitals.o2Saturation}%</span></p>
            `;
        }

        // File info
        if (reviewFile && this.assessmentData.file) {
            reviewFile.innerHTML = `
                <p><strong>File:</strong> <span>${this.assessmentData.file.name}</span></p>
                <p><strong>Size:</strong> <span>${this.assessmentData.file.size} MB</span></p>
                <p><strong>Format:</strong> <span>${this.assessmentData.file.type.toUpperCase()}</span></p>
            `;
        }
    }

    // ============================================
    // SUBMISSION
    // ============================================

    submitAssessment() {
        if (!this.assessmentData.file || !this.assessmentData.patient.name || !this.assessmentData.vitals.heartRate) {
            this.showNotification('Please complete all fields.', 'error');
            return;
        }

        // Show loading
        this.showNotification('Submitting assessment...', 'info');

        // Simulate API call
        setTimeout(() => {
            this.showNotification('Assessment submitted successfully!', 'success');
            
            // Redirect after delay
            setTimeout(() => {
                window.location.href = '/dashboard';
            }, 1500);
        }, 2000);
    }

    // ============================================
    // UTILITIES
    // ============================================

    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.style.cssText = `
            position: fixed;
            top: 100px;
            right: 20px;
            background: ${type === 'success' ? '#00D98E' : type === 'error' ? '#FF2E63' : '#00D9FF'};
            color: white;
            padding: 16px 24px;
            border-radius: 10px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
            z-index: 1000;
            animation: slideInRight 0.3s ease-out;
            font-weight: 600;
            max-width: 400px;
        `;
        notification.textContent = message;

        document.body.appendChild(notification);

        // Remove after delay
        setTimeout(() => {
            notification.style.animation = 'slideOutRight 0.3s ease-out';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }

    setupNavigation() {
        // Sidebar navigation is handled by navigation.js
        // This ensures the sidebar works properly
        const navItems = document.querySelectorAll('.nav-item');
        navItems.forEach(item => {
            const href = item.getAttribute('href');
            if (href === '/new-assessment') {
                item.classList.add('active');
            } else {
                item.classList.remove('active');
            }
        });
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new AssessmentManager();
});

// Add animation styles dynamically
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from {
            opacity: 0;
            transform: translateX(100px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }

    @keyframes slideOutRight {
        from {
            opacity: 1;
            transform: translateX(0);
        }
        to {
            opacity: 0;
            transform: translateX(100px);
        }
    }
`;
document.head.appendChild(style);
