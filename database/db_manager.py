import sqlite3
import bcrypt
import json
from datetime import datetime
from pathlib import Path

class DatabaseManager:
    """Cloud-compatible database manager for CAD evaluation system"""
    
    def __init__(self, db_path='database/cad_evaluation.db'):
        self.db_path = db_path
        # Ensure database directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.init_database()
    
    def get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path, check_same_thread=False)
    
    def init_database(self):
        """Initialize database with schema"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('faculty', 'student')),
                department TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Experiments table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS experiments (
                experiment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_code TEXT NOT NULL,
                experiment_name TEXT NOT NULL,
                description TEXT,
                reference_model_path TEXT NOT NULL,
                created_by INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deadline TEXT,
                is_active BOOLEAN DEFAULT 1,
                grading_thresholds TEXT,
                FOREIGN KEY (created_by) REFERENCES users(user_id)
            )
        ''')
        
        # Submissions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS submissions (
                submission_id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_id INTEGER NOT NULL,
                student_id INTEGER NOT NULL,
                submission_file_path TEXT,
                submission_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                evaluation_status TEXT DEFAULT 'pending',
                FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id),
                FOREIGN KEY (student_id) REFERENCES users(user_id),
                UNIQUE(experiment_id, student_id)
            )
        ''')
        
        # Evaluation results table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS evaluation_results (
                result_id INTEGER PRIMARY KEY AUTOINCREMENT,
                submission_id INTEGER NOT NULL,
                letter_grade TEXT NOT NULL,
                numerical_score REAL NOT NULL,
                mean_deviation REAL,
                max_deviation REAL,
                std_deviation REAL,
                percentile_95 REAL,
                hausdorff_distance REAL,
                detailed_feedback TEXT,
                pdf_report_path TEXT,
                evaluated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (submission_id) REFERENCES submissions(submission_id)
            )
        ''')
        
        # Audit log
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_log (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT NOT NULL,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')
        
        conn.commit()
        conn.close()
        
        # Create default admin user if not exists
        self.create_default_admin()
    
    def create_default_admin(self):
        """Create default admin account"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE role = ?', ('faculty',))
        if cursor.fetchone()[0] == 0:
            # Create default admin
            password_hash = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt())
            cursor.execute('''
                INSERT INTO users (username, password_hash, full_name, email, role, department)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', ('admin', password_hash, 'System Administrator', 'admin@university.edu', 'faculty', 'Engineering'))
            conn.commit()
        
        conn.close()
    
    def reset_user_password(self, user_id, new_password):
        """Reset a user's password (admin function)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
            cursor.execute('UPDATE users SET password_hash = ? WHERE user_id = ?', 
                          (password_hash, user_id))
            conn.commit()
            
            # Get username for logging
            cursor.execute('SELECT username FROM users WHERE user_id = ?', (user_id,))
            username = cursor.fetchone()[0]
            
            self.log_action(user_id, 'password_reset', f'Password reset by admin for user: {username}')
            return True, "Password reset successfully"
        except Exception as e:
            return False, str(e)
        finally:
            conn.close()
    
    def get_all_students(self):
        """Get all student users"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT user_id, username, full_name, email, department, created_at
            FROM users
            WHERE role = 'student'
            ORDER BY full_name
        ''')
        
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()
        return results
    
    # USER MANAGEMENT
    def register_user(self, username, password, full_name, email, role='student', department=None):
        """Register new user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            cursor.execute('''
                INSERT INTO users (username, password_hash, full_name, email, role, department)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (username, password_hash, full_name, email, role, department))
            conn.commit()
            user_id = cursor.lastrowid
            self.log_action(user_id, 'user_registered', f'New {role} registered: {username}')
            return True, user_id
        except sqlite3.IntegrityError as e:
            return False, str(e)
        finally:
            conn.close()
    
    def authenticate_user(self, username, password):
        """Authenticate user login"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT user_id, password_hash, role, full_name FROM users WHERE username = ?', (username,))
        result = cursor.fetchone()
        conn.close()
        
        if result and bcrypt.checkpw(password.encode('utf-8'), result[1]):
            self.log_action(result[0], 'user_login', f'User {username} logged in')
            return True, {'user_id': result[0], 'role': result[2], 'full_name': result[3], 'username': username}
        return False, None
    
    # EXPERIMENT MANAGEMENT
    def create_experiment(self, experiment_code, experiment_name, description, 
                         reference_model_path, created_by, deadline=None, grading_thresholds=None):
        """Create new experiment"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            thresholds_json = json.dumps(grading_thresholds) if grading_thresholds else None
            cursor.execute('''
                INSERT INTO experiments (experiment_code, experiment_name, description, 
                                       reference_model_path, created_by, deadline, grading_thresholds)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (experiment_code, experiment_name, description, reference_model_path, 
                  created_by, deadline, thresholds_json))
            conn.commit()
            experiment_id = cursor.lastrowid
            self.log_action(created_by, 'experiment_created', f'Created experiment: {experiment_code}')
            return True, experiment_id
        except sqlite3.IntegrityError as e:
            return False, str(e)
        finally:
            conn.close()
    
    def get_active_experiments(self):
        """Get all active experiments"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT e.*, u.full_name as creator_name
            FROM experiments e
            JOIN users u ON e.created_by = u.user_id
            WHERE e.is_active = 1
            ORDER BY e.created_at DESC
        ''')
        
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()
        return results
    
    def get_experiment_by_id(self, experiment_id):
        """Get experiment details"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM experiments WHERE experiment_id = ?', (experiment_id,))
        columns = [desc[0] for desc in cursor.description]
        result = cursor.fetchone()
        conn.close()
        
        return dict(zip(columns, result)) if result else None
    
    # SUBMISSION MANAGEMENT
    def create_submission(self, experiment_id, student_id, submission_file_path):
        """Create or update student submission"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO submissions 
                (experiment_id, student_id, submission_file_path, submission_date, evaluation_status)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP, 'pending')
            ''', (experiment_id, student_id, submission_file_path))
            conn.commit()
            submission_id = cursor.lastrowid
            self.log_action(student_id, 'submission_created', 
                          f'Submitted for experiment ID: {experiment_id}')
            return True, submission_id
        except Exception as e:
            return False, str(e)
        finally:
            conn.close()
    
    def get_student_submissions(self, student_id):
        """Get all submissions for a student"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT s.*, e.experiment_name, e.experiment_code,
                   er.letter_grade, er.numerical_score, er.pdf_report_path
            FROM submissions s
            JOIN experiments e ON s.experiment_id = e.experiment_id
            LEFT JOIN evaluation_results er ON s.submission_id = er.submission_id
            WHERE s.student_id = ?
            ORDER BY s.submission_date DESC
        ''', (student_id,))
        
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()
        return results
    
    def update_submission_status(self, submission_id, status):
        """Update submission evaluation status"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE submissions SET evaluation_status = ? WHERE submission_id = ?', 
                      (status, submission_id))
        conn.commit()
        conn.close()
    
    # EVALUATION RESULTS
    def save_evaluation_result(self, submission_id, grade_data, feedback, pdf_path):
        """Save evaluation results"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO evaluation_results 
            (submission_id, letter_grade, numerical_score, mean_deviation, max_deviation,
             std_deviation, percentile_95, hausdorff_distance, detailed_feedback, pdf_report_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (submission_id, grade_data['letter_grade'], grade_data['numerical_score'],
              grade_data.get('mean_deviation'), grade_data.get('max_deviation'),
              grade_data.get('std_deviation'), grade_data.get('percentile_95'),
              grade_data.get('hausdorff_distance'), feedback, pdf_path))
        
        conn.commit()
        conn.close()
        self.update_submission_status(submission_id, 'evaluated')
    
    def get_all_results_for_faculty(self, faculty_id=None):
        """Get all evaluation results (for faculty dashboard)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = '''
            SELECT u.username, u.full_name, u.email,
                   e.experiment_code, e.experiment_name,
                   s.submission_date,
                   er.letter_grade, er.numerical_score,
                   er.mean_deviation, er.pdf_report_path,
                   er.evaluated_at
            FROM users u
            JOIN submissions s ON u.user_id = s.student_id
            JOIN experiments e ON s.experiment_id = e.experiment_id
            LEFT JOIN evaluation_results er ON s.submission_id = er.submission_id
            WHERE u.role = 'student'
        '''
        
        if faculty_id:
            query += ' AND e.created_by = ?'
            cursor.execute(query + ' ORDER BY s.submission_date DESC', (faculty_id,))
        else:
            cursor.execute(query + ' ORDER BY s.submission_date DESC')
        
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()
        return results
    
    # AUDIT LOG
    def log_action(self, user_id, action, details):
        """Log system action"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO audit_log (user_id, action, details)
            VALUES (?, ?, ?)
        ''', (user_id, action, details))
        conn.commit()
        conn.close()
    
    def get_audit_log(self, limit=100):
        """Get recent audit log entries"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT al.*, u.username, u.full_name
            FROM audit_log al
            LEFT JOIN users u ON al.user_id = u.user_id
            ORDER BY al.timestamp DESC
            LIMIT ?
        ''', (limit,))
        
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()
        return results
