from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.pdfgen import canvas
from datetime import datetime
import io
from pathlib import Path

class PDFReportGenerator:
    """Generate professional PDF evaluation reports"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1f77b4'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#2ca02c'),
            spaceAfter=12,
            spaceBefore=12,
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='CustomBody',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceAfter=8,
            alignment=TA_JUSTIFY
        ))
    
    def generate_evaluation_report(self, output_path, student_info, experiment_info, 
                                   evaluation_results):
        """Generate complete evaluation report PDF"""
        
        # Ensure output directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Create PDF document
        doc = SimpleDocTemplate(output_path, pagesize=letter,
                               rightMargin=72, leftMargin=72,
                               topMargin=72, bottomMargin=18)
        
        # Container for PDF elements
        story = []
        
        # Title
        title = Paragraph(
            "CAD MODEL EVALUATION REPORT",
            self.styles['CustomTitle']
        )
        story.append(title)
        story.append(Spacer(1, 0.3*inch))
        
        # Student Information Section
        story.append(Paragraph("Student Information", self.styles['CustomHeading']))
        
        student_data = [
            ['Student Name:', student_info.get('full_name', 'N/A')],
            ['Student ID:', student_info.get('username', 'N/A')],
            ['Email:', student_info.get('email', 'N/A')],
            ['Submission Date:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        ]
        
        student_table = Table(student_data, colWidths=[2*inch, 4*inch])
        student_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e8f4f8')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey)
        ]))
        story.append(student_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Experiment Information Section
        story.append(Paragraph("Experiment Information", self.styles['CustomHeading']))
        
        experiment_data = [
            ['Experiment Code:', experiment_info.get('experiment_code', 'N/A')],
            ['Experiment Name:', experiment_info.get('experiment_name', 'N/A')],
            ['Description:', experiment_info.get('description', 'N/A')[:100] + '...']
        ]
        
        experiment_table = Table(experiment_data, colWidths=[2*inch, 4*inch])
        experiment_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e8f4f8')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey)
        ]))
        story.append(experiment_table)
        story.append(Spacer(1, 0.4*inch))
        
        # Evaluation Results Section
        grade_data = evaluation_results.get('grade', {})
        letter_grade = grade_data.get('letter_grade', 'F')
        numerical_score = grade_data.get('numerical_score', 0)
        
        # Grade display with color coding
        grade_color = self._get_grade_color(letter_grade)
        
        story.append(Paragraph("Evaluation Results", self.styles['CustomHeading']))
        
        grade_text = f'<font size="36" color="{grade_color}"><b>{letter_grade}</b></font> ({numerical_score}%)'
        grade_para = Paragraph(grade_text, self.styles['CustomTitle'])
        story.append(grade_para)
        story.append(Spacer(1, 0.2*inch))
        
        # Geometric Analysis Results
        story.append(Paragraph("Geometric Accuracy Analysis", self.styles['CustomHeading']))
        
        geo_analysis = evaluation_results.get('geometric_analysis', {})
        
        analysis_data = [
            ['Metric', 'Value', 'Status'],
            ['Mean Deviation', f"{geo_analysis.get('mean_deviation', 0):.4f} units", 
             self._get_status_icon(geo_analysis.get('mean_deviation', 0), 0.5)],
            ['Maximum Deviation', f"{geo_analysis.get('max_deviation', 0):.4f} units",
             self._get_status_icon(geo_analysis.get('max_deviation', 0), 2.0)],
            ['Standard Deviation', f"{geo_analysis.get('std_deviation', 0):.4f} units", '-'],
            ['95th Percentile', f"{geo_analysis.get('percentile_95', 0):.4f} units", '-'],
            ['Hausdorff Distance', f"{geo_analysis.get('hausdorff_distance', 0):.4f} units", '-']
        ]
        
        analysis_table = Table(analysis_data, colWidths=[2.5*inch, 2*inch, 1.5*inch])
        analysis_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f77b4')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(analysis_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Detailed Feedback
        story.append(Paragraph("Detailed Feedback", self.styles['CustomHeading']))
        
        feedback_text = evaluation_results.get('feedback', 'No feedback available')
        # Convert feedback to HTML-safe format
        feedback_paragraphs = feedback_text.split('\n')
        for para in feedback_paragraphs:
            if para.strip():
                story.append(Paragraph(para.strip(), self.styles['CustomBody']))
        
        story.append(Spacer(1, 0.3*inch))
        
        # Grading Scale Reference
        story.append(Paragraph("Grading Scale Reference", self.styles['CustomHeading']))
        
        scale_data = [
            ['Grade', 'Deviation Range', 'Score Range'],
            ['A', '≤ 0.1 units', '95-100%'],
            ['B', '≤ 0.5 units', '85-94%'],
            ['C', '≤ 1.0 units', '75-84%'],
            ['D', '≤ 2.0 units', '65-74%'],
            ['F', '> 2.0 units', '0-64%']
        ]
        
        scale_table = Table(scale_data, colWidths=[1.5*inch, 2.5*inch, 2*inch])
        scale_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2ca02c')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        story.append(scale_table)
        
        # Footer
        story.append(Spacer(1, 0.5*inch))
        footer_text = f"Generated on {datetime.now().strftime('%Y-%m-%d at %H:%M:%S')} | CAD Evaluation System"
        footer = Paragraph(footer_text, self.styles['Normal'])
        story.append(footer)
        
        # Build PDF
        doc.build(story)
        
        return output_path
    
    def _get_grade_color(self, grade):
        """Get color code for grade"""
        colors_map = {
            'A': '#2ca02c',  # Green
            'B': '#17becf',  # Cyan
            'C': '#ff7f0e',  # Orange
            'D': '#d62728',  # Red
            'F': '#8b0000'   # Dark Red
        }
        return colors_map.get(grade, '#000000')
    
    def _get_status_icon(self, value, threshold):
        """Get status icon based on threshold"""
        if value <= threshold:
            return '✓'
        elif value <= threshold * 2:
            return '⚠'
        else:
            return '✗'
