import os
import shutil
from pathlib import Path
from datetime import datetime
import hashlib

class FileManager:
    """Cloud-compatible file management system"""
    
    def __init__(self):
        self.base_dir = Path('data')
        self.experiments_dir = self.base_dir / 'experiments'
        self.submissions_dir = self.base_dir / 'submissions'
        self.reports_dir = self.base_dir / 'reports'
        
        # Create directories
        self._setup_directories()
    
    def _setup_directories(self):
        """Create necessary directories"""
        self.experiments_dir.mkdir(parents=True, exist_ok=True)
        self.submissions_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
    
    def save_experiment_file(self, uploaded_file, experiment_code):
        """Save faculty-uploaded experiment reference model"""
        try:
            # Create experiment-specific directory
            exp_dir = self.experiments_dir / experiment_code
            exp_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate safe filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            file_ext = Path(uploaded_file.name).suffix
            filename = f"reference_model_{timestamp}{file_ext}"
            
            file_path = exp_dir / filename
            
            # Save file
            with open(file_path, 'wb') as f:
                f.write(uploaded_file.getbuffer())
            
            return str(file_path), filename
            
        except Exception as e:
            raise Exception(f"Error saving experiment file: {str(e)}")
    
    def save_student_submission(self, uploaded_file, experiment_code, student_username):
        """Save student submission (temporary)"""
        try:
            # Create submission directory
            submission_dir = self.submissions_dir / experiment_code / student_username
            submission_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            file_ext = Path(uploaded_file.name).suffix
            filename = f"submission_{timestamp}{file_ext}"
            
            file_path = submission_dir / filename
            
            # Save file
            with open(file_path, 'wb') as f:
                f.write(uploaded_file.getbuffer())
            
            return str(file_path), filename
            
        except Exception as e:
            raise Exception(f"Error saving submission: {str(e)}")
    
    def save_pdf_report(self, pdf_path, experiment_code, student_username):
        """Save PDF report to permanent storage"""
        try:
            # Create report directory
            report_dir = self.reports_dir / experiment_code
            report_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate report filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_filename = f"{student_username}_{timestamp}_report.pdf"
            report_path = report_dir / report_filename
            
            # Copy PDF to permanent location
            shutil.copy2(pdf_path, report_path)
            
            return str(report_path)
            
        except Exception as e:
            raise Exception(f"Error saving PDF report: {str(e)}")
    
    def delete_student_submission(self, submission_file_path):
        """Delete student submission file after evaluation"""
        try:
            if submission_file_path and os.path.exists(submission_file_path):
                os.remove(submission_file_path)
                
                # Clean up empty directories
                parent_dir = Path(submission_file_path).parent
                if parent_dir.exists() and not any(parent_dir.iterdir()):
                    parent_dir.rmdir()
                    
                return True
            return False
            
        except Exception as e:
            print(f"Warning: Could not delete submission file: {str(e)}")
            return False
    
    def get_experiment_reference_path(self, experiment_id, reference_filename):
        """Get full path to experiment reference model"""
        # This assumes the path is stored in database
        # Return the path as-is if it exists, otherwise search
        if os.path.exists(reference_filename):
            return reference_filename
        
        # Search in experiments directory
        for exp_dir in self.experiments_dir.iterdir():
            if exp_dir.is_dir():
                for file in exp_dir.iterdir():
                    if file.name == reference_filename or str(file) == reference_filename:
                        return str(file)
        
        raise FileNotFoundError(f"Reference model not found: {reference_filename}")
    
    def cleanup_old_submissions(self, days_old=30):
        """Clean up old submission files (maintenance function)"""
        cutoff_time = datetime.now().timestamp() - (days_old * 24 * 3600)
        deleted_count = 0
        
        try:
            for submission_path in self.submissions_dir.rglob('*'):
                if submission_path.is_file():
                    file_time = submission_path.stat().st_mtime
                    if file_time < cutoff_time:
                        submission_path.unlink()
                        deleted_count += 1
            
            # Clean up empty directories
            for dirpath in sorted(self.submissions_dir.rglob('*'), reverse=True):
                if dirpath.is_dir() and not any(dirpath.iterdir()):
                    dirpath.rmdir()
            
            return deleted_count
            
        except Exception as e:
            print(f"Error during cleanup: {str(e)}")
            return deleted_count
    
    def get_file_info(self, file_path):
        """Get file information"""
        try:
            path = Path(file_path)
            if path.exists():
                stat = path.stat()
                return {
                    'size': stat.st_size,
                    'size_mb': round(stat.st_size / (1024 * 1024), 2),
                    'created': datetime.fromtimestamp(stat.st_ctime),
                    'modified': datetime.fromtimestamp(stat.st_mtime),
                    'extension': path.suffix,
                    'name': path.name
                }
            return None
        except Exception as e:
            return None
    
    def validate_cad_file(self, file_path):
        """Validate CAD file format"""
        valid_extensions = ['.obj', '.stl', '.ply', '.off', '.STEP']
        ext = Path(file_path).suffix.lower()
        
        if ext not in valid_extensions:
            return False, f"Unsupported file format: {ext}"
        
        # Check file size (max 100MB)
        file_size = Path(file_path).stat().st_size
        max_size = 100 * 1024 * 1024  # 100MB
        
        if file_size > max_size:
            return False, f"File too large: {round(file_size/(1024*1024), 2)}MB (max 100MB)"
        
        return True, "Valid CAD file"
    
    def get_storage_stats(self):
        """Get storage statistics"""
        stats = {
            'experiments': 0,
            'submissions': 0,
            'reports': 0,
            'total': 0
        }
        
        try:
            for directory, key in [
                (self.experiments_dir, 'experiments'),
                (self.submissions_dir, 'submissions'),
                (self.reports_dir, 'reports')
            ]:
                size = sum(f.stat().st_size for f in directory.rglob('*') if f.is_file())
                stats[key] = round(size / (1024 * 1024), 2)  # MB
            
            stats['total'] = sum([stats['experiments'], stats['submissions'], stats['reports']])
            
        except Exception as e:
            print(f"Error calculating storage: {str(e)}")
        
        return stats
