// ============================================
// ASSESSMENT PAGE - FUNCTIONALITY
// ============================================

class AssessmentManager {
    constructor() {
        this.currentFile = null;
        this.results = null;
        this.init();
    }

    init() {
        console.log('AssessmentManager initialized');
        this.setupFileUpload();
        this.setupEventListeners();
    }

    // ============================================
    // FILE UPLOAD HANDLING
    // ============================================

    setupFileUpload() {
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');
        const filePreview = document.getElementById('filePreview');
        const analyzeBtn = document.getElementById('analyzeBtn');
        const removeFile = document.getElementById('removeFile');

        if (!uploadArea || !fileInput) {
            console.error('Upload elements not found!');
            return;
        }

        console.log('Setting up file upload...');

        // Click to upload
        uploadArea.addEventListener('click', () => {
            console.log('Upload area clicked');
            fileInput.click();
        });

        // File input change
        fileInput.addEventListener('change', (e) => {
            console.log('File input changed');
            if (e.target.files.length > 0) {
                this.handleFileSelect(e.target.files[0], uploadArea, filePreview, analyzeBtn);
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
                this.handleFileSelect(e.dataTransfer.files[0], uploadArea, filePreview, analyzeBtn);
            }
        });

        // Remove file
        if (removeFile) {
            removeFile.addEventListener('click', () => {
                console.log('Remove file clicked');
                fileInput.value = '';
                this.currentFile = null;
                filePreview.style.display = 'none';
                uploadArea.style.display = 'block';
                this.updateAnalyzeButtonState(analyzeBtn);
            });
        }
    }

    handleFileSelect(file, uploadArea, filePreview, analyzeBtn) {
        console.log('Processing file:', file.name);
        
        // Validate file

        const allowedExtensions = ['csv', 'xml', 'mat', 'pdf', 'jpg', 'jpeg', 'png'];
        const fileExt = file.name.split('.').pop().toLowerCase();
        const maxSize = 10 * 1024 * 1024; // 10MB

        console.log('File extension:', fileExt);
        console.log('File size:', (file.size / 1024 / 1024).toFixed(2), 'MB');

        if (!allowedExtensions.includes(fileExt)) {
            this.showNotification(`Invalid file format (.${fileExt}). Supported: csv, xml, mat, pdf, jpg, jpeg, png`, 'error');
            return;
        }

        if (file.size > maxSize) {
            this.showNotification(`File is too large (${(file.size / 1024 / 1024).toFixed(2)}MB). Maximum size is 10MB.`, 'error');
            return;
        }

        // Store file
        this.currentFile = file;

        // Update UI
        if (document.getElementById('fileName')) {
            document.getElementById('fileName').textContent = file.name;
        }
        if (document.getElementById('fileSize')) {
            document.getElementById('fileSize').textContent = `${(file.size / 1024 / 1024).toFixed(2)} MB`;
        }

        uploadArea.style.display = 'none';
        filePreview.style.display = 'flex';
        
        // Update analyze button state based on both file and patient selection
        this.updateAnalyzeButtonState(analyzeBtn);
        if (analyzeBtn) {
            console.log('Analyze button state updated');
        }
        
        this.showNotification(`File "${file.name}" uploaded successfully!`, 'success');
    }

    // ============================================
    // EVENT LISTENERS
    // ============================================

    setupEventListeners() {
        // Analyze button
        const analyzeBtn = document.getElementById('analyzeBtn');
        const patientSelect = document.getElementById('patientSelect');
        const fileInput = document.getElementById('fileInput');
        
        if (analyzeBtn) {
            analyzeBtn.addEventListener('click', () => {
                this.analyzeECG();
            });
        }

        // Patient selection validation
        if (patientSelect) {
            patientSelect.addEventListener('change', () => {
                this.updateAnalyzeButtonState(analyzeBtn);
            });
        }

        // File input validation
        if (fileInput) {
            fileInput.addEventListener('change', () => {
                this.updateAnalyzeButtonState(analyzeBtn);
            });
        }

        // Cancel button
        const cancelBtn = document.querySelector('.btn-secondary');
        if (cancelBtn) {
            cancelBtn.addEventListener('click', (e) => {
                if (e.target.textContent.includes('Cancel')) {
                    window.location.href = '/dashboard';
                }
            });
        }
    }

    updateAnalyzeButtonState(analyzeBtn) {
        if (!analyzeBtn) return;
        
        const patientSelect = document.getElementById('patientSelect');
        const patientSelected = patientSelect && patientSelect.value !== '';
        const fileSelected = this.currentFile !== null;
        
        analyzeBtn.disabled = !(patientSelected && fileSelected);
    }

    // ============================================
    // ECG ANALYSIS
    // ============================================

    async analyzeECG() {
        if (!this.currentFile) {
            this.showNotification('Please select a file first', 'error');
            return;
        }

        const patientId = document.getElementById('patientSelect').value;
        if (!patientId) {
            this.showNotification('Please select a patient first', 'error');
            return;
        }

        const formData = new FormData();
        formData.append('file', this.currentFile);

        try {
            // Show loading
            this.showNotification('Analyzing ECG file...', 'info');
            
            console.log('Sending file for analysis...');
            
            // Submit form directly (will reload page with results)
            const form = document.getElementById('uploadForm');
            if (form) {
                // Add file to form
                const fileInput = document.getElementById('realFileInput');
                if (fileInput) {
                    const dataTransfer = new DataTransfer();
                    dataTransfer.items.add(this.currentFile);
                    fileInput.files = dataTransfer.files;
                }
                form.submit();
            } else {
                // Fallback: use AJAX
                const response = await fetch('/new-assessment', {
                    method: 'POST',
                    body: formData
                });

                if (response.ok || response.redirected) {
                    window.location.reload();
                } else {
                    this.showNotification('Analysis failed. Please try again.', 'error');
                }
            }
        } catch (error) {
            console.error('Analysis error:', error);
            this.showNotification('Network error. Please try again.', 'error');
        }
    }

    // ============================================
    // UTILITIES
    // ============================================

    showNotification(message, type = 'info') {
        console.log('Notification:', type, message);
        
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
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, initializing AssessmentManager');
    new AssessmentManager();
});