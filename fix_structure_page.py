import json

target_url = "https://lgu.edu.pk/structure-of-bs-cs-programme/"

full_text = """BS Computer Science
Structure of the Program
The curriculum of Bachelor of Computer Science has been adopted as per the guidelines of National Computing Education Accreditation Council. The detailed distribution of the program as per NCEAC Criteria is shown in table below:

Generic Structure for LGU NCEAC Curriculum 2024 for BSCS
Program Structure Overview:
Computing Core: 46 Credit Hours, 14 Courses
Domain Core: 18 Credit Hours, 6 Courses
Domain Elective: 21 Credit Hours, 7 Courses
Major Courses (Core + Domain Core + Domain Elective): 85 Credit Hours, 27 Courses
Mathematics & Supporting Courses/Interdisciplinary Courses: 12 Credit Hours, 4 Courses
Elective Supporting Course: 3 Credit Hours, 1 Course
General Education Requirement: 32 Credit Hours, 14 Courses
University Core: 0 Credit Hours, 1 Course
Total: 132 Credit Hours, 47 Courses

COMPUTING CORE COURSES (46 Credit Hours):
1. CC6101 Programming Fundamentals - 4 Credit Hours
2. CC6202 Object Oriented Programming - 4 Credit Hours
3. CC6203 Database Systems - 4 Credit Hours
4. CC6204 Digital Logic Design - 3 Credit Hours
5. CC6410 Computer Organization & Assembly Language - 3 Credit Hours
6. CC6305 Data Structures - 4 Credit Hours
7. CC6307 Artificial Intelligence - 3 Credit Hours
8. CC6306 Information Security - 3 Credit Hours
9. CC6511 Operating Systems - 3 Credit Hours
10. CC6309 Software Engineering - 3 Credit Hours
11. CC6312 Analysis of Algorithms - 3 Credit Hours
12. CC6308 Computer Networks - 3 Credit Hours
13. CC6713 Final Year Project I - 2 Credit Hours
14. CC6814 Final Year Project II - 4 Credit Hours

DOMAIN CORE COURSES (19 Credit Hours):
1. CSC6301 Theory of Automata - 3 Credit Hours
2. CSC6402 Advance Database Management Systems - 3 Credit Hours
3. CSC6503 HCI & Computer Graphics - 3 Credit Hours
4. CSC6504 Computer Architecture - 3 Credit Hours
5. CSC6605 Compiler Construction - 3 Credit Hours
6. CSC6606 Parallel & Distributed Computing - 4 Credit Hours

DOMAIN ELECTIVE COURSES (21 Credit Hours) - 7 electives chosen from this list:
Mobile App Development, Web Design and Development, Machine Learning, Deep Learning,
Digital Image Processing, Game Design and Development, Computer Vision, Cloud Computing,
Computer Graphics, Big Data, Distributed Computing, Data and Network Security,
Fundamentals of Data Mining, Internet of Things, Wireless Networks, Social Computing,
Data Warehousing, Expert Systems, Artificial Neural Networks, Fuzzy Logic,
Human Computer Interaction, Computational Intelligence, Multi Agent Systems,
Natural Language Processing, Logical Paradigms of Computing,
Formal Methods for Software Engineering, Software Quality Assurance, Big Data Analysis

MATHEMATICS & SUPPORTING COURSES (12 Credit Hours):
1. MATH6608 Linear Algebra - 3 Credit Hours
2. MATH6507 Multivariable Calculus - 3 Credit Hours
3. MATH6608 Probability & Statistics - 3 Credit Hours
4. EN6304 Technical and Business Writing - 3 Credit Hours

ELECTIVE SUPPORTING COURSES (3 Credit Hours) - chosen from:
Financial Accounting, Introduction to Psychology, Human Resource Management, Social Work Practice

GENERAL EDUCATION REQUIREMENT (32 Credit Hours):
1. COMPS6101 Application of Information & Communication Technologies - 3 Credit Hours
2. PHYS6103 Natural Science (Applied Physics) - 3 Credit Hours
3. PAK6101 Ideology and Constitution of Pakistan - 2 Credit Hours
4. MATH6101 QR 1 (Calculus and Analytic Geometry) / Fundamentals of Math 1 - 3 Credit Hours
5. EN6202 Functional English - 3 Credit Hours
6. ISL6101 Islamic Studies - 2 Credit Hours
7. CCE6101 Civics and Community Engagement - 2 Credit Hours
8. ALD6201 Arts & Humanities (Professional Practices) - 2 Credit Hours
9. ALD6204 Entrepreneurship - 2 Credit Hours
10. EN6302 Expository Writing - 3 Credit Hours
11. MATH6406 QR 2 (Discrete Structures) - 3 Credit Hours
12. ALD6206 Social Science (e.g. Introduction to Management) - 2 Credit Hours
13. TQL6405 Quranic Studies - 1 Credit Hour

UNIVERSITY CORE (0 Credit Hours):
1. CC6705 Internship - 0 Credit Hours

Important Notes:
1. One credit hour equals 3 contact hours for Lab courses and 1 contact hour for theory courses.
2. Elective courses in CS, CS Supporting, and General Education domains are selected each semester from the elective list based on instructor availability, market trend, and student registration numbers.
3. Codes for ALD- and CSE- electives are assigned by the Department based on the selected elective course.
"""

updated_items = []
found = False

with open("lgu_merged.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        item = json.loads(line)
        if item.get("url", "").rstrip("/") == target_url.rstrip("/"):
            item["text"] = full_text
            found = True
        updated_items.append(item)

if not found:
    # If it wasn't in the file at all, add it as a new entry
    updated_items.append({
        "url": target_url,
        "title": "Structure of BS (CS) Programme",
        "text": full_text,
        "tables": [],
        "scraped_at": "manual-fix"
    })

with open("lgu_merged.jsonl", "w", encoding="utf-8") as f:
    for item in updated_items:
        f.write(json.dumps(item) + "\n")

print("Updated! Found existing entry:", found)
print("Total items in file:", len(updated_items))
