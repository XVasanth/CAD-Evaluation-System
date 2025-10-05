import numpy as np
import trimesh
from sklearn.neighbors import NearestNeighbors
from typing import Dict, Any
import warnings
warnings.filterwarnings('ignore')

class CADEvaluator:
    """CAD Model Evaluation Engine - Cloud Compatible"""
    
    def __init__(self):
        self.grading_thresholds = {
            'A': 0.1,
            'B': 0.5,
            'C': 1.0,
            'D': 2.0,
            'F': float('inf')
        }
        
        self.detailed_scoring = {
            'A': (95, 100),
            'B': (85, 94),
            'C': (75, 84),
            'D': (65, 74),
            'F': (0, 64)
        }
    
    def load_mesh(self, file_path):
        """Load mesh from file"""
        try:
            loaded = trimesh.load(file_path)
            
            if isinstance(loaded, trimesh.Scene):
                if len(loaded.geometry) == 0:
                    raise Exception("No geometry found in file")
                elif len(loaded.geometry) == 1:
                    return list(loaded.geometry.values())[0]
                else:
                    return loaded.dump(concatenate=True)
            return loaded
        except Exception as e:
            raise Exception(f"Error loading mesh: {str(e)}")
    
    def extract_point_cloud(self, mesh, num_points=2048):
        """Extract normalized point cloud from mesh"""
        if mesh.is_watertight:
            points, _ = trimesh.sample.sample_surface(mesh, num_points)
        else:
            if len(mesh.vertices) >= num_points:
                indices = np.random.choice(len(mesh.vertices), num_points, replace=False)
                points = mesh.vertices[indices]
            else:
                indices = np.random.choice(len(mesh.vertices), num_points, replace=True)
                points = mesh.vertices[indices]
        
        # Normalize to unit sphere
        points = points - np.mean(points, axis=0)
        scale = np.max(np.sqrt(np.sum(points**2, axis=1)))
        if scale > 0:
            points = points / scale
        
        return points.astype(np.float32)
    
    def compute_geometric_differences(self, teacher_points, student_points):
        """Compute geometric differences between models"""
        nn_t2s = NearestNeighbors(n_neighbors=1)
        nn_t2s.fit(student_points)
        distances_t2s, _ = nn_t2s.kneighbors(teacher_points)
        
        nn_s2t = NearestNeighbors(n_neighbors=1)
        nn_s2t.fit(teacher_points)
        distances_s2t, _ = nn_s2t.kneighbors(student_points)
        
        distances_t2s = distances_t2s.flatten()
        distances_s2t = distances_s2t.flatten()
        
        return {
            'teacher_to_student_distances': distances_t2s,
            'student_to_teacher_distances': distances_s2t,
            'mean_deviation': np.mean(distances_t2s),
            'max_deviation': np.max(distances_t2s),
            'std_deviation': np.std(distances_t2s),
            'median_deviation': np.median(distances_t2s),
            'percentile_95': np.percentile(distances_t2s, 95),
            'percentile_99': np.percentile(distances_t2s, 99),
            'hausdorff_distance': max(np.max(distances_t2s), np.max(distances_s2t))
        }
    
    def calculate_grade(self, geometric_results):
        """Calculate letter grade and numerical score"""
        mean_dev = geometric_results['mean_deviation']
        max_dev = geometric_results['max_deviation']
        
        letter_grade = 'F'
        for grade, threshold in self.grading_thresholds.items():
            if mean_dev <= threshold:
                letter_grade = grade
                break
        
        min_score, max_score = self.detailed_scoring[letter_grade]
        
        if letter_grade == 'A':
            score_factor = max(0, 1 - (mean_dev / self.grading_thresholds['A']))
            numerical_score = min_score + (max_score - min_score) * score_factor
        elif letter_grade == 'F':
            numerical_score = max(0, min_score - (mean_dev * 10))
        else:
            prev_grade = list(self.grading_thresholds.keys())[
                list(self.grading_thresholds.keys()).index(letter_grade) - 1
            ]
            prev_threshold = self.grading_thresholds[prev_grade]
            curr_threshold = self.grading_thresholds[letter_grade]
            score_factor = (curr_threshold - mean_dev) / (curr_threshold - prev_threshold)
            numerical_score = min_score + (max_score - min_score) * score_factor
        
        if max_dev > 5.0:
            numerical_score -= 10
        elif max_dev > 3.0:
            numerical_score -= 5
        
        numerical_score = max(0, min(100, numerical_score))
        
        return {
            'letter_grade': letter_grade,
            'numerical_score': round(numerical_score, 1),
            'mean_deviation': mean_dev,
            'max_deviation': max_dev,
            'std_deviation': geometric_results['std_deviation'],
            'percentile_95': geometric_results['percentile_95'],
            'hausdorff_distance': geometric_results['hausdorff_distance']
        }
    
    def generate_feedback(self, grading_results, geometric_results):
        """Generate detailed feedback"""
        mean_dev = geometric_results['mean_deviation']
        max_dev = geometric_results['max_deviation']
        
        feedback = f"""
📊 CAD MODEL EVALUATION REPORT
{'='*60}

📈 OVERALL PERFORMANCE:
Grade: {grading_results['letter_grade']} ({grading_results['numerical_score']}%)

📏 GEOMETRIC ACCURACY ANALYSIS:
• Mean Deviation: {mean_dev:.4f} units
• Maximum Deviation: {max_dev:.4f} units
• Standard Deviation: {geometric_results['std_deviation']:.4f} units
• 95th Percentile: {geometric_results['percentile_95']:.4f} units
• Hausdorff Distance: {geometric_results['hausdorff_distance']:.4f} units

🎯 DETAILED ASSESSMENT:
"""
        
        if grading_results['letter_grade'] == 'A':
            feedback += """
✅ EXCELLENT WORK!
• Your model shows exceptional accuracy
• All dimensions are within professional tolerances
• Geometric precision meets industry standards
• Continue this level of attention to detail!
"""
        elif grading_results['letter_grade'] == 'B':
            feedback += f"""
✅ GOOD WORK with room for improvement:
• Most dimensions are accurate (within {self.grading_thresholds['B']:.1f} units)
• Some areas need refinement
• Focus on improving precision in critical dimensions
"""
        elif grading_results['letter_grade'] == 'C':
            feedback += f"""
⚠️ ACCEPTABLE but needs significant improvement:
• Basic geometry is correct but lacks precision
• Several dimensions exceed acceptable tolerances
• Mean deviation of {mean_dev:.3f} needs to be reduced
• Review modeling techniques and double-check dimensions
"""
        elif grading_results['letter_grade'] == 'D':
            feedback += f"""
⚠️ NEEDS MAJOR REVISION:
• Significant geometric inaccuracies detected
• Multiple dimensions are far from specifications
• Mean deviation of {mean_dev:.3f} is too high
• Consider starting over with careful attention
"""
        else:
            feedback += f"""
❌ UNSATISFACTORY - MAJOR ISSUES:
• Model has serious geometric problems
• Mean deviation of {mean_dev:.3f} indicates fundamental errors
• Max deviation of {max_dev:.3f} suggests missing features
• Please review assignment requirements
"""
        
        feedback += "\n🔧 IMPROVEMENT RECOMMENDATIONS:\n"
        
        if geometric_results['std_deviation'] > 0.5:
            feedback += "• High variation - focus on consistent precision\n"
        
        if max_dev > 2 * mean_dev:
            feedback += "• Some areas have major errors - check features\n"
        
        if geometric_results['percentile_95'] > self.grading_thresholds['C']:
            feedback += "• 95% of points should be more accurate\n"
        
        feedback += f"""
📋 GRADING SCALE:
• A: ≤{self.grading_thresholds['A']:.1f} units
• B: ≤{self.grading_thresholds['B']:.1f} units
• C: ≤{self.grading_thresholds['C']:.1f} units
• D: ≤{self.grading_thresholds['D']:.1f} units
"""
        
        return feedback
    
    def evaluate(self, teacher_model_path, student_model_path, num_points=2048):
        """Complete evaluation workflow"""
        try:
            # Load meshes
            teacher_mesh = self.load_mesh(teacher_model_path)
            student_mesh = self.load_mesh(student_model_path)
            
            # Extract point clouds
            teacher_points = self.extract_point_cloud(teacher_mesh, num_points)
            student_points = self.extract_point_cloud(student_mesh, num_points)
            
            # Compute differences
            geometric_results = self.compute_geometric_differences(
                teacher_points, student_points
            )
            
            # Calculate grade
            grading_results = self.calculate_grade(geometric_results)
            
            # Generate feedback
            feedback = self.generate_feedback(grading_results, geometric_results)
            
            return {
                'success': True,
                'grade': grading_results,
                'geometric_analysis': geometric_results,
                'feedback': feedback,
                'teacher_points': teacher_points,
                'student_points': student_points
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
