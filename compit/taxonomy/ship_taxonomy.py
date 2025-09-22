import csv
import zipfile
from io import StringIO, BytesIO

def create_ship_pbs():

    # ----------------------------
    # 1. Main CSV Template content
    # ----------------------------
    main_headers = [
        "id", "parent_id", "pbs_code", "name", "type", "discipline", "function_type",
        "system", "medium", "tightness", "location_zone", "location_deck",
        "location_frame_start", "location_frame_end", "location_y",
        "sfi_code", "rds_function", "rds_product", "rds_location",
        "class_rule_ref", "design_status", "design_status_date",
        "design_status_user", "comments"
    ]

    # Example rows (simplified but following PBS & rules)
    main_rows = [
        # id, parent_id, pbs_code, name, type, discipline, function_type, system, medium, tightness, zone, deck, frame_start, frame_end, y, sfi, rds_f, rds_p, rds_l, class_ref, status, date, user, comments
        ["1", "", "1", "Hull & Structure", "group", "Structure", "", "", "", "", "Z01", "D00", "", "", "", "100", "=HULL", "+SHIP", "-D00-000-S00", "DNV Pt.3 Ch.1", "for_class", "2025-08-14", "user", ""],
        ["1.1", "1", "1.1", "Shell Plating", "panel", "Structure", "SHELL", "", "", "weathertight", "Z01", "D00", "0", "20", "S00", "100.1", "=HULL", "+PL01", "-D00-000-S00", "DNV Pt.3 Ch.3 Sec.1", "for_class", "2025-08-14", "user", "Grade AH36, t=20mm"],
        ["1.3", "1", "1.3", "Decks", "group", "Structure", "", "", "", "", "Z01", "D10", "", "", "", "101", "=HULL", "+DK01", "-D10-000-S00", "DNV Pt.3 Ch.3 Sec.5", "for_class", "2025-08-14", "user", ""],
        ["1.3.1", "1.3", "1.3.1", "Main Deck Panel", "panel", "Structure", "DECK", "", "", "weathertight", "Z01", "D10", "0", "40", "S00", "101.1", "=HULL", "+DKMD", "-D10-000-S00", "DNV Pt.3 Ch.3 Sec.5", "for_class", "2025-08-14", "user", "Grade AH36, t=15mm"],
        ["2", "", "2", "Propulsion & Maneuvering", "group", "Mechanical", "", "Propulsion", "", "", "Z01", "D00", "", "", "", "200", "=P1", "+PROP", "-D00-000-S00", "", "for_class", "2025-08-14", "user", ""],
        ["2.1", "2", "2.1", "Main Engine", "equipment", "Mechanical", "", "Propulsion", "fuel oil", "", "Z01", "D00", "10", "20", "S00", "2010", "=P1", "+M1", "-D00-010-S00", "DNV Pt.4 Ch.2", "for_class", "2025-08-14", "user", ""],
        ["4", "", "4", "Piping & Utilities", "group", "Piping", "", "", "", "", "Z01", "D00", "", "", "", "400", "=U1", "+PIPE", "-D00-000-S00", "", "for_class", "2025-08-14", "user", ""],
        ["4.11", "4", "4.11", "Fire Main", "system", "Piping", "", "Fire Main", "water", "weathertight", "Z02", "D10", "80", "120", "S05", "4411", "=F1", "+FM", "-D10-080-S05", "DNV Pt.4 Ch.6", "for_class", "2025-08-14", "user", ""],
        ["9", "", "9", "Deck Machinery & Mooring", "group", "Mechanical", "", "", "", "", "Z03", "D10", "", "", "", "900", "=M1", "+DM", "-D10-000-S00", "", "for_class", "2025-08-14", "user", ""],
        ["9.1", "9", "9.1", "Windlass", "equipment", "Mechanical", "", "Mooring", "", "", "Z03", "D10", "0", "10", "S00", "9010", "=M1", "+WL", "-D10-000-S00", "DNV Pt.4 Ch.14", "for_class", "2025-08-14", "user", ""],
    ]

    main_csv_io = StringIO()
    writer = csv.writer(main_csv_io)
    writer.writerow(main_headers)
    writer.writerows(main_rows)
    main_csv_content = main_csv_io.getvalue()

    return main_csv_content

def write_csv(csv_bytes:BytesIO, csv_file:str):
    """
    Write CSV content to a file.

    :param csv_bytes: BytesIO object containing CSV content.
    :param csv_file: Path to the output CSV file.
    """
    with open(csv_file, 'wb') as f:
        f.write(csv_bytes.getvalue())

def write_excel(xlsx_bytes:BytesIO, xlsx_file:str):
    """
    Write Excel content to a file.

    :param xlsx_bytes: BytesIO object containing Excel content.
    :param xlsx_file: Path to the output Excel file.
    """
    with open(xlsx_file, 'wb') as f:
        f.write(xlsx_bytes.getvalue())


def create_sfi_cheat_sheet():
    """

    :return:
        BytesIO object containing the SFI cheat sheet CSV content.
    """
    # ----------------------------
    # 2. SFI Cheat-Sheet content
    # ----------------------------
    sfi_headers = ["sfi_code", "description", "notes"]
    sfi_rows = [
        ["100", "Hull", "Main hull structure including shell plating"],
        ["101", "Decks", "All decks including superstructure decks"],
        ["1010", "Main Deck", "Main deck plating and stiffeners"],
        ["1011", "Upper Deck", "Upper deck plating and stiffeners"],
        ["102", "Shell Plating", "Side shell and bottom plating"],
        ["1020", "Side Shell", "Side shell plating including sheer strake"],
        ["1021", "Bottom Shell", "Flat bottom and bilge plating"],
        ["103", "Bulkheads", "Transverse and longitudinal bulkheads"],
        ["1030", "Watertight Bulkheads", "Structural WT bulkheads"],
        ["1031", "Weathertight Bulkheads", "Structural weather bulkheads"],
        ["104", "Superstructure", "Accommodation and bridge superstructures"],
        ["1040", "Accommodation Block", "Crew living spaces superstructure"],
        ["1041", "Bridge Structure", "Navigational bridge deckhouse"],
        ["105", "Foundations", "Equipment seating and structural supports"],
        ["1050", "Main Engine Foundations", "Foundations for propulsion machinery"],
        ["1051", "Auxiliary Foundations", "Foundations for auxiliary machinery"],

        ["200", "Propulsion Plant", "Prime movers, gearboxes, shafts, propellers"],
        ["2010", "Main Engine", "Slow-speed or medium-speed diesel"],
        ["2011", "Reduction Gear", "Main gearbox"],
        ["2020", "Propeller", "Fixed or controllable pitch propeller"],
        ["2021", "Shaftline", "Intermediate and propeller shafts"],
        ["2030", "Steering Gear", "Hydraulic or electric steering system"],
        ["2031", "Rudder", "Rudder blade and stock"],

        ["300", "Electrical Power Generation & Distribution", "Generators, switchboards, distribution"],
        ["3010", "Main Generators", "Ship service generators"],
        ["3011", "Emergency Generator", "Emergency power source"],
        ["3020", "Main Switchboard", "Main electrical distribution board"],
        ["3021", "Emergency Switchboard", "Emergency electrical distribution board"],
        ["3030", "Transformers", "Voltage conversion transformers"],
        ["3031", "Frequency Converters", "AC/AC or AC/DC drives"],

        ["400", "Piping Systems", "Main groups by medium"],
        ["4410", "Fire Main", "Sea water fire-fighting distribution"],
        ["4411", "Fire Pumps", "Main and emergency fire pumps"],
        ["4510", "Fuel Oil System", "Fuel storage, transfer, treatment"],
        ["4511", "Fuel Oil Transfer", "Fuel transfer pumps and lines"],
        ["4512", "Fuel Oil Purification", "Separators and filters"],
        ["4520", "Lubricating Oil System", "LO storage, transfer, treatment"],
        ["4530", "Cooling Water System", "HT and LT cooling water circuits"],
        ["4540", "Sea Water Service", "Sea water pumps, strainers, distribution"],
        ["4550", "Compressed Air System", "Start, control, and service air"],

        ["500", "Navigation, Communications & Bridge", "Navigational and comms equipment"],
        ["5010", "Radar Systems", "X- and S-band radar"],
        ["5011", "ECDIS", "Electronic chart display systems"],
        ["5020", "GMDSS", "Global maritime distress and safety system"],
        ["5030", "AIS", "Automatic identification system"],

        ["600", "Control, Automation & Monitoring", "IAS, sensors, control systems"],
        ["6010", "Integrated Automation System", "Main ship monitoring and control"],
        ["6020", "Tank Level Gauging", "Cargo and ballast tank level measurement"],

        ["700", "Safety, LSA & Closures", "Lifesaving, firefighting, closures"],
        ["7010", "Fire Detection System", "Smoke and heat detection"],
        ["7020", "Lifeboats", "Totally enclosed lifeboats"],
        ["7021", "Rescue Boats", "Fast rescue craft"],
        ["7030", "Davits", "Boat launching appliances"],

        ["800", "Cargo Systems & Handling", "Cargo spaces and handling gear"],
        ["8010", "Cargo Cranes", "Derricks, cranes, and hoists"],
        ["8020", "Cargo Ventilation", "Hold ventilation systems"],

        ["900", "Deck Machinery & Mooring", "Anchor and mooring systems"],
        ["9010", "Windlass", "Anchor handling machinery"],
        ["9020", "Mooring Winches", "Berthing and mooring winches"],
        ["9030", "Capstans", "Warps and rope handling"],
    ]
    sfi_csv_io = StringIO()
    writer = csv.writer(sfi_csv_io)
    writer.writerow(sfi_headers)
    writer.writerows(sfi_rows)
    sfi_csv_content = sfi_csv_io.getvalue()

    return sfi_csv_content
