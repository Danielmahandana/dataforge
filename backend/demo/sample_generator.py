from __future__ import annotations
import os
from pathlib import Path
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


class SampleGenerator:
    """Generates realistic synthetic South African labour-market & education PDFs using ReportLab."""

    @classmethod
    def generate_tvet_qualifications_pdf(cls, output_path: str) -> str:
        """Generates a multi-page TVET qualifications list with 1:N college offerings and repeated headers."""
        target = Path(output_path).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)

        doc = SimpleDocTemplate(
            str(target),
            pagesize=landscape(letter),
            leftMargin=25,
            rightMargin=25,
            topMargin=25,
            bottomMargin=25,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontSize=13,
            leading=15,
            textColor=colors.HexColor('#1D3557'),
        )
        cell_style = ParagraphStyle(
            'CellStyle',
            parent=styles['Normal'],
            fontSize=8,
            leading=10,
        )
        header_style = ParagraphStyle(
            'HeaderStyle',
            parent=styles['Normal'],
            fontSize=8,
            leading=10,
            textColor=colors.white,
            fontName='Helvetica-Bold',
        )

        elements = []
        elements.append(Paragraph("DHET / QCTO PUBLIC TVET COLLEGES: REGISTERED OCCUPATIONAL QUALIFICATIONS", title_style))
        elements.append(Paragraph("Official Annexure: Priority Occupational Certificates and Participating Delivery Institutions", styles['Normal']))
        elements.append(Spacer(1, 10))

        headers = ["SAQA ID", "Qualification Title", "NQF", "Framework", "NSFAS", "Participating Colleges"]
        
        raw_p1 = [
            ["118792", "Occupational Certificate: Artificial Intelligence Software Developer", "5", "OQSF", "Yes", "Motheo TVET College; Umfolozi TVET College; Flavius Mareka TVET College"],
            ["118793", "Occupational Certificate: Cloud Computing Systems Engineer", "6", "OQSF", "Yes", "Ekurhuleni East TVET College; Tshwane South TVET College"],
            ["102145", "Occupational Certificate: Renewable Energy Technician (Solar PV)", "5", "OQSF", "Yes", "Northern Cape Urban TVET; Boland TVET College; South West Gauteng TVET"],
            ["98912", "Occupational Certificate: Automated Mechatronics Technician", "5", "OQSF", "Yes", "False Bay TVET College; Port Elizabeth TVET College"],
            ["117894", "Occupational Certificate: Cybersecurity Analyst", "6", "OQSF", "Yes", "Vhembe TVET College; Central Johannesburg TVET; Coastal TVET College"],
            ["101344", "Occupational Certificate: Industrial Robotics Programmer", "5", "OQSF", "Yes", "Orbit TVET College; Northlink TVET College"],
        ]

        data_p1 = [[Paragraph(h, header_style) for h in headers]]
        for row in raw_p1:
            data_p1.append([Paragraph(str(c), cell_style) for c in row])

        # Available printable width: landscape letter (792pt) - 50pt margins = 742pt
        # Column widths: 60, 220, 35, 65, 45, 310 = 735pt
        t1 = Table(data_p1, colWidths=[60, 220, 35, 65, 45, 310])
        t1.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1D3557')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#1D3557')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
        ]))
        elements.append(t1)

        # Page 2: Continuation table
        elements.append(PageBreak())
        elements.append(Paragraph("DHET PUBLIC TVET COLLEGES: REGISTERED OCCUPATIONAL QUALIFICATIONS (CONTINUED)", title_style))
        elements.append(Spacer(1, 10))

        raw_p2 = [
            ["119451", "Occupational Certificate: Data Operations Specialist", "5", "OQSF", "Yes", "Sedibeng TVET College; Westcol TVET College"],
            ["103445", "Occupational Certificate: Digital Additive Manufacturing Machinist", "4", "OQSF", "No", "Taletso TVET College; Goldfields TVET College"],
            ["112340", "Occupational Certificate: Precision Toolmaker", "5", "OQSF", "Yes", "Tshwane North TVET; Buffalo City TVET; Lovedale TVET College"],
            ["118800", "Occupational Certificate: Quantum Algorithm Developer", "7", "HEQSF", "No", "South West Gauteng TVET; Waterberg TVET College"],
        ]

        data_p2 = [[Paragraph(h, header_style) for h in headers]]
        for row in raw_p2:
            data_p2.append([Paragraph(str(c), cell_style) for c in row])

        t2 = Table(data_p2, colWidths=[60, 220, 35, 65, 45, 310])
        t2.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1D3557')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#1D3557')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
        ]))
        elements.append(t2)

        doc.build(elements)
        return str(target)

    @classmethod
    def generate_qlfs_codebook_pdf(cls, output_path: str) -> str:
        """Generates a realistic Stats SA QLFS survey codebook."""
        target = Path(output_path).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)

        doc = SimpleDocTemplate(
            str(target),
            pagesize=letter,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontSize=13,
            leading=15,
            textColor=colors.HexColor('#1D3557'),
        )
        cell_style = ParagraphStyle(
            'CellStyle',
            parent=styles['Normal'],
            fontSize=8,
            leading=10,
        )
        header_style = ParagraphStyle(
            'HeaderStyle',
            parent=styles['Normal'],
            fontSize=9,
            leading=11,
            textColor=colors.white,
            fontName='Helvetica-Bold',
        )

        elements = []
        elements.append(Paragraph("STATISTICS SOUTH AFRICA: QUARTERLY LABOUR FORCE SURVEY (QLFS)", title_style))
        elements.append(Paragraph("Metadata Dictionary, Variable Descriptions and Category Codebook", styles['Normal']))
        elements.append(Spacer(1, 12))

        headers = ["Variable Name", "Variable Label", "Value", "Value Label"]
        raw_rows = [
            ["Q13GENDER", "Gender of Respondent", "1", "Male"],
            ["Q13GENDER", "Gender of Respondent", "2", "Female"],
            ["Q21PROVINCE", "Province of Residence", "1", "Western Cape"],
            ["Q21PROVINCE", "Province of Residence", "2", "Eastern Cape"],
            ["Q21PROVINCE", "Province of Residence", "3", "Northern Cape"],
            ["Q21PROVINCE", "Province of Residence", "4", "Free State"],
            ["Q21PROVINCE", "Province of Residence", "5", "KwaZulu-Natal"],
            ["Q21PROVINCE", "Province of Residence", "6", "North West"],
            ["Q21PROVINCE", "Province of Residence", "7", "Gauteng"],
            ["Q21PROVINCE", "Province of Residence", "8", "Mpumalanga"],
            ["Q21PROVINCE", "Province of Residence", "9", "Limpopo"],
            ["Q31EMPLOYMENT", "Employment Status", "1", "Employed"],
            ["Q31EMPLOYMENT", "Employment Status", "2", "Unemployed (Official Definition)"],
            ["Q31EMPLOYMENT", "Employment Status", "3", "Discouraged Work Seeker"],
            ["Q31EMPLOYMENT", "Employment Status", "4", "Other Not Economically Active"],
        ]

        data = [[Paragraph(h, header_style) for h in headers]]
        for r in raw_rows:
            data.append([Paragraph(str(c), cell_style) for c in r])

        t = Table(data, colWidths=[110, 190, 50, 190])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1D3557')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#1D3557')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
        ]))
        elements.append(t)

        doc.build(elements)
        return str(target)

    @classmethod
    def generate_oihd_report_pdf(cls, output_path: str) -> str:
        """Generates a realistic DHET Occupations in High Demand report."""
        target = Path(output_path).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)

        doc = SimpleDocTemplate(
            str(target),
            pagesize=letter,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontSize=13,
            leading=15,
            textColor=colors.HexColor('#1D3557'),
        )
        cell_style = ParagraphStyle(
            'CellStyle',
            parent=styles['Normal'],
            fontSize=8,
            leading=10,
        )
        header_style = ParagraphStyle(
            'HeaderStyle',
            parent=styles['Normal'],
            fontSize=8,
            leading=10,
            textColor=colors.white,
            fontName='Helvetica-Bold',
        )

        elements = []
        elements.append(Paragraph("DHET OCCUPATIONS IN HIGH DEMAND (OIHD): EVIDENCE REPORT", title_style))
        elements.append(Paragraph("Annexure A: National Top Priority Occupations List and Educational Thresholds", styles['Normal']))
        elements.append(Spacer(1, 12))

        headers = ["OFO Code", "Occupation Title", "Rank", "Major Group", "Province", "Entry Qualification"]
        raw_rows = [
            ["251201", "Software Developer", "1", "Professionals", "National", "Bachelor Degree / NQF 7"],
            ["251202", "Developer Programmer", "2", "Professionals", "National", "Diploma / NQF 6"],
            ["251101", "Systems Analyst", "3", "Professionals", "Gauteng", "Bachelor Degree / NQF 7"],
            ["214904", "Solar Energy Systems Engineer", "4", "Professionals", "Northern Cape", "BSc Engineering / NQF 8"],
            ["311501", "Mechanical Engineering Technologist", "5", "Technicians", "Eastern Cape", "Advanced Diploma / NQF 7"],
            ["651202", "Welder (Specialized)", "6", "Craft Workers", "Mpumalanga", "Occupational Certificate / NQF 4"],
            ["252101", "Database Administrator", "7", "Professionals", "Western Cape", "Bachelor Degree / NQF 7"],
        ]

        data = [[Paragraph(h, header_style) for h in headers]]
        for r in raw_rows:
            data.append([Paragraph(str(c), cell_style) for c in r])

        t = Table(data, colWidths=[65, 160, 35, 85, 70, 125])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1D3557')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#1D3557')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
        ]))
        elements.append(t)

        doc.build(elements)
        return str(target)
