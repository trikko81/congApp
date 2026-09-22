import os
import sys
from pathlib import Path
import httpx
import pymupdf

"""
Script to collect or construct real-world municipal agenda PDF packets for TownWatch.
Saves packets to TEMPPDF/sample_agendas/
"""

SAMPLE_DIR = Path("TEMPPDF/sample_agendas").resolve()
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)

MUNICIPAL_PACKETS = [
    {
        "filename": "Virginia_Beach_City_Council_Agenda_2026.pdf",
        "municipality": "City of Virginia Beach",
        "date": "May 12, 2026",
        "items": [
            {
                "title": "CONSENT AGENDA ITEM 1: APPROVAL OF MINUTES",
                "text": "Motion to approve official minutes of the April 28, 2026 regular council session as recorded.",
                "category": "General Governance & Administration"
            },
            {
                "title": "ORDINANCE NO. 2026-102: RESIDENTIAL VARIANCE AT 450 NORTH ELM STREET",
                "text": (
                    "AN ORDINANCE AMENDING THE ZONING ORDINANCE OF THE CITY OF VIRGINIA BEACH.\n"
                    "The City Council hereby approves the application of Elm Street Residences LLC for a variance on "
                    "Tax Map Parcel 104-55-A, located at 450 North Elm Street. The variance permits reducing the minimum "
                    "rear yard setback from 25 feet to 15 feet to accommodate multi-family townhome construction.\n"
                    "Conditions of approval require construction of an engineered stormwater runoff basin."
                ),
                "category": "Zoning & Land Use"
            },
            {
                "title": "RESOLUTION NO. 2026-44: FISCAL YEAR 2026-2027 REAL PROPERTY TAX LEVY",
                "text": (
                    "A RESOLUTION FIXING THE TAX RATE ON REAL PROPERTY FOR TAX YEAR 2026.\n"
                    "BE IT RESOLVED by the Council of the City of Virginia Beach that the real property tax rate is established "
                    "at $0.99 per $100 of assessed valuation. Estimated general fund real estate tax revenues will total $682,000,000.\n"
                    "Dedicated capital millage includes 0.45 mills for regional public schools and storm mitigation bonds."
                ),
                "category": "Taxes & Budget"
            },
            {
                "title": "PUBLIC HEARING ITEM 4: CONDITIONAL USE PERMIT FOR DATA CENTER ON PACIFIC AVENUE",
                "text": (
                    "Application of Mid-Atlantic Data Infrastructure for a conditional use permit on Parcel 208-14-B "
                    "at 1250 Pacific Avenue. Public testimony taken regarding acoustic shielding and grid interconnection limits."
                ),
                "category": "Zoning & Land Use"
            },
            {
                "title": "ACTION ITEM 5: SCHOOL BOARD MODERNIZATION BOND ALLOCATION",
                "text": (
                    "Authorization of $4,200,000 in municipal general obligation bond proceeds allocated to Virginia Beach "
                    "City Public Schools for HVAC retrofitting and STEM laboratory equipment at 820 Atlantic Avenue."
                ),
                "category": "Education & School Board"
            },
            {
                "title": "RESOLUTION NO. 2026-78: EMERGENCY RADIO REPEATER LEASE AT 782 SOUTH OAK STREET",
                "text": (
                    "PUBLIC SAFETY COMMUNICATIONS RESOLUTION.\n"
                    "Authorizing execution of an emergency communications repeater antenna lease on tower facility located at "
                    "782 South Oak Street. Provides critical mission radio coverage for Police Department and Emergency Medical Services."
                ),
                "category": "Public Safety & Infrastructure"
            },
            {
                "title": "RESOLUTION NO. 2026-89: RIVERWALK GREENWAY EXTENSION AND TREE CANOPY GRANT",
                "text": (
                    "Acceptance of $650,000 Virginia Urban Forestry Grant to install 400 native shade trees along the "
                    "Riverwalk trail corridor from Broad Street to 500 Commerce Avenue."
                ),
                "category": "Parks & Environment"
            }
        ]
    },
    {
        "filename": "Fairfax_County_Board_Supervisors_Agenda_2026.pdf",
        "municipality": "Fairfax County",
        "date": "June 16, 2026",
        "items": [
            {
                "title": "ACTION ITEM 1: ADOPTION OF STORMWATER MANAGEMENT FEE SCHEDULE",
                "text": (
                    "Board of Supervisors resolution adopting revised commercial and residential stormwater utility rates. "
                    "Standard single-family dwelling quarterly fee adjusted to $24.50 to support watershed protection."
                ),
                "category": "Taxes & Budget"
            },
            {
                "title": "PUBLIC HEARING: REZONING APPLICATION RZ-2026-08 AT 9200 MAIN STREET",
                "text": (
                    "Public hearing on application of Commonwealth Development Partners to rezone 4.5 acres at 9200 Main Street "
                    "from C-2 Commercial to Mixed-Use High Density (PRM). Subject property includes Tax Parcel 058-2-01-0012."
                ),
                "category": "Zoning & Land Use"
            },
            {
                "title": "ITEM 3: FAIRFAX COUNTY PUBLIC SCHOOLS BUS FLEET ELECTRIFICATION",
                "text": (
                    "Authorization for Superintendent to execute contract for 35 zero-emission electric school buses "
                    "funded through EPA Clean School Bus program grant awards."
                ),
                "category": "Education & School Board"
            },
            {
                "title": "ITEM 4: PUBLIC SAFETY CAD DISPATCH SYSTEM UPGRADE",
                "text": (
                    "Award of $1,800,000 contract for modernizing 911 Computer-Aided Dispatch (CAD) software and tactical "
                    "in-vehicle terminals for the Fairfax County Police Department."
                ),
                "category": "Public Safety & Infrastructure"
            }
        ]
    }
]

def build_pdf_packet(packet_def: dict, out_path: Path):
    doc = pymupdf.open()
    
    # Cover / Header Page
    page = doc.new_page(width=612, height=792)
    # Header banner
    page.draw_rect(pymupdf.Rect(40, 40, 572, 100), color=(0.1, 0.2, 0.4), fill=(0.92, 0.94, 0.98))
    page.insert_textbox(
        pymupdf.Rect(50, 48, 562, 70),
        packet_def["municipality"].upper(),
        fontsize=14,
        fontname="helv",
        color=(0.1, 0.2, 0.4)
    )
    page.insert_textbox(
        pymupdf.Rect(50, 72, 562, 95),
        f"OFFICIAL MEETING AGENDA PACKET • {packet_def['date'].upper()}",
        fontsize=10,
        fontname="helv",
        color=(0.3, 0.3, 0.3)
    )

    y_cursor = 120
    for idx, item in enumerate(packet_def["items"], 1):
        if y_cursor > 650:
            page = doc.new_page(width=612, height=792)
            y_cursor = 50

        # Item Header
        page.draw_rect(pymupdf.Rect(40, y_cursor, 572, y_cursor + 24), color=(0.8, 0.8, 0.8), fill=(0.96, 0.96, 0.96))
        page.insert_textbox(
            pymupdf.Rect(45, y_cursor + 4, 565, y_cursor + 20),
            item["title"],
            fontsize=9,
            fontname="helv",
            color=(0.1, 0.1, 0.1)
        )
        y_cursor += 30

        # Item Body Text
        text_rect = pymupdf.Rect(45, y_cursor, 565, y_cursor + 90)
        page.insert_textbox(
            text_rect,
            item["text"],
            fontsize=9,
            fontname="helv",
            color=(0.2, 0.2, 0.2)
        )
        y_cursor += 100

    doc.save(str(out_path))
    doc.close()
    print(f"Generated municipal agenda packet: {out_path} ({out_path.stat().st_size} bytes)")

def collect_all():
    print("Collecting and building municipal agenda packets...")
    for pdef in MUNICIPAL_PACKETS:
        out_file = SAMPLE_DIR / pdef["filename"]
        build_pdf_packet(pdef, out_file)
    print(f"All sample agenda packets collected in {SAMPLE_DIR}")

if __name__ == "__main__":
    collect_all()
