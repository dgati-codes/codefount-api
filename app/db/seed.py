"""
app/db/seed.py
===============
Seeds the database with all initial data from the frontend mockData.

Spring Boot equivalent
-----------------------
  data.sql / import.sql loaded by Spring Boot on startup,
  OR a @Component ApplicationRunner that checks-and-inserts seed rows.

Run:  python -m app.db.seed
"""

import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

# ── CRITICAL: import every model explicitly BEFORE create_all ────────────────
# SQLAlchemy's MetaData registry only knows about tables whose ORM classes have
# been imported into the current Python process.  A wildcard "import *" is NOT
# sufficient — Python may skip sub-imports.  Import in FK-dependency order so
# SQLAlchemy can resolve all foreign-key references when it sorts the DDL.
# Spring Boot equivalent: @EntityScan("com.codefount.models")
from app.models.user import User, UserRole                        # ① no FKs
from app.models.course import Course, CurriculumItem, Enrollment  # ② FK → users/courses
from app.models.workshop import Workshop, WorkshopRegistration    # ③ FK → users/workshops
from app.models.misc import Service, Schedule, Enquiry            # ④ FK → users (nullable)

from app.db.session import AsyncSessionLocal, engine

logger = logging.getLogger("seed")
logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")


# ── Seed data (mirrors frontend mockData.js) ──────────────────────────────────

COURSES = [
    dict(id=1, title="Java Full Stack", category="Java Fullstack", trainer="Mr. Sai",
         fee=3500, offer=2200, color="#0f766e", tag="BESTSELLER", duration="4 Months",
         level="Beginner → Advanced", mode=["Online", "Classroom"],
         desc="Master Java, Spring Boot, React and Microservices.",
         outcome="Graduate ready to build full enterprise Java applications.",
         highlights=["Spring Boot 3 & Spring Security","React.js + Redux Toolkit",
                     "Microservices & REST APIs","MySQL + MongoDB","AWS Deployment"],
         curriculum=[
             ("Wk 1–2","Core Java & OOP",1), ("Wk 3–4","Advanced Java – Streams",2),
             ("Wk 5–6","Spring Boot & REST",3), ("Wk 7–8","Spring Security & JWT",4),
             ("Wk 9–10","React.js & Frontend",5), ("Wk 11–12","Microservices",6),
             ("Wk 13–14","AWS & CI/CD",7), ("Wk 15–16","Live Project",8),
         ]),
    dict(id=2, title="DevOps with Multi-Cloud", category="DevOps", trainer="Mr. Ravi",
         fee=3000, offer=1900, color="#7c3aed", tag="HOT", duration="3 Months",
         level="Intermediate", mode=["Online"],
         desc="Master CI/CD, Docker, Kubernetes and multi-cloud on AWS, Azure and GCP.",
         outcome="Design production CI/CD pipelines across AWS, Azure and GCP.",
         highlights=["Docker & Kubernetes","Jenkins & GitLab CI","Terraform IaC","AWS + Azure + GCP"],
         curriculum=[
             ("Wk 1–2","Linux & Shell Scripting",1), ("Wk 3–4","Docker & Containers",2),
             ("Wk 5–6","Kubernetes & Helm",3), ("Wk 7–8","Jenkins CI/CD",4),
             ("Wk 9–10","Terraform & IaC",5), ("Wk 11–12","Multi-Cloud",6),
         ]),
    dict(id=3, title="Cyber Security", category="Cyber Security", trainer="Mr. Dal",
         fee=2800, offer=1800, color="#0d9488", tag="", duration="3 Months",
         level="Beginner → Intermediate", mode=["Online","Classroom"],
         desc="Ethical hacking, penetration testing and SOC operations.",
         outcome="Certified and hands-on ready for penetration testing or SOC roles.",
         highlights=["Ethical Hacking","Network Security","SIEM & SOC","CompTIA Security+ Prep"],
         curriculum=[
             ("Wk 1–2","Networking & Security Basics",1), ("Wk 3–4","Ethical Hacking",2),
             ("Wk 5–6","Vulnerability Assessment",3), ("Wk 7–8","Web App Security",4),
             ("Wk 9–10","SOC & Incident Response",5), ("Wk 11–12","CTF Capstone",6),
         ]),
    dict(id=4, title="Generative AI", category="AI/ML", trainer="Mr. Sithu",
         fee=3200, offer=2000, color="#5b21b6", tag="NEW", duration="3 Months",
         level="Intermediate", mode=["Online"],
         desc="Master LLMs, prompt engineering, RAG systems and production AI apps.",
         outcome="Build and deploy production LLM-powered applications.",
         highlights=["LLMs & Prompt Engineering","OpenAI API & LangChain","RAG & Vector DBs"],
         curriculum=[
             ("Wk 1–2","Python for AI",1), ("Wk 3–4","LLMs & APIs",2),
             ("Wk 5–6","LangChain",3), ("Wk 7–8","RAG & Vector DBs",4),
             ("Wk 9–10","Fine-tuning",5), ("Wk 11–12","Capstone",6),
         ]),
    dict(id=5, title="AWS Bootcamp", category="Cloud Computing", trainer="Mr. Ashok",
         fee=2500, offer=1500, color="#b45309", tag="NEW", duration="2.5 Months",
         level="Beginner → Advanced", mode=["Online","Hybrid"],
         desc="Get AWS certified and prepare for AWS Solutions Architect Associate.",
         outcome="Walk out SAA-C03 exam-ready with real hands-on lab experience.",
         highlights=["EC2, S3, RDS, VPC","Lambda & Serverless","AWS SAA Exam Prep"],
         curriculum=[
             ("Wk 1–2","AWS Core – EC2, S3, IAM",1), ("Wk 3–4","Networking",2),
             ("Wk 5–6","Databases",3), ("Wk 7–8","Serverless",4), ("Wk 9–10","Exam Prep",5),
         ]),
    dict(id=6, title="MERN Stack", category="Java Fullstack", trainer="Mr. Kiran",
         fee=2800, offer=1700, color="#0e7490", tag="", duration="3 Months",
         level="Beginner → Intermediate", mode=["Online","Classroom"],
         desc="Build full-stack apps with MongoDB, Express, React and Node.",
         outcome="Graduate with 3 deployed MERN applications.",
         highlights=["React.js + Redux","Node.js & Express","MongoDB","JWT Auth"],
         curriculum=[
             ("Wk 1–3","JavaScript ES6+ & Node.js",1), ("Wk 4–6","Express & MongoDB",2),
             ("Wk 7–9","React.js & Redux",3), ("Wk 10–12","Projects & Deploy",4),
         ]),
    dict(id=7, title="Data Analytics", category="Data Science", trainer="Mr. Naresh",
         fee=2600, offer=1600, color="#15803d", tag="", duration="2.5 Months",
         level="Beginner", mode=["Online"],
         desc="Turn data into business insights with Python, SQL and Power BI.",
         outcome="Analyse, visualise and report on real business datasets.",
         highlights=["Python & Pandas","SQL","Power BI","Tableau"],
         curriculum=[
             ("Wk 1–2","Python & Pandas",1), ("Wk 3–4","SQL",2),
             ("Wk 5–6","Visualisation",3), ("Wk 7–8","Power BI",4), ("Wk 9–10","Capstone",5),
         ]),
    dict(id=8, title="Python Fullstack", category="Python Fullstack", trainer="Mr. Ram",
         fee=2700, offer=1750, color="#dc2626", tag="", duration="3 Months",
         level="Beginner → Intermediate", mode=["Online"],
         desc="Build web apps with Python, Django REST APIs and React.",
         outcome="Build and deploy full-stack Django + React applications.",
         highlights=["Python 3","Django & DRF","PostgreSQL","React.js","Docker"],
         curriculum=[
             ("Wk 1–3","Python Core",1), ("Wk 4–6","Django APIs",2),
             ("Wk 7–9","React Frontend",3), ("Wk 10–12","Docker & Deploy",4),
         ]),
    dict(id=9, title=".NET Core Fullstack", category="Dot NET", trainer="Mr. Suresh",
         fee=2400, offer=1550, color="#9333ea", tag="", duration="3 Months",
         level="Intermediate", mode=["Online","Classroom"],
         desc="Build enterprise apps with C#, ASP.NET Core and React.",
         outcome="Build enterprise .NET applications and target Microsoft tech roles.",
         highlights=["C# & OOP","ASP.NET Core Web API","Entity Framework","Azure"],
         curriculum=[
             ("Wk 1–3","C# Fundamentals",1), ("Wk 4–6","ASP.NET Core APIs",2),
             ("Wk 7–9","EF Core & SQL Server",3), ("Wk 10–12","React + Azure",4),
         ]),
    dict(id=10, title="Digital Marketing", category="Digital Marketing", trainer="Ms. Priya",
         fee=1800, offer=1100, color="#be185d", tag="", duration="2 Months",
         level="Beginner", mode=["Online","Classroom"],
         desc="Master SEO, Google Ads and analytics to launch a marketing career.",
         outcome="Run paid and organic digital campaigns independently.",
         highlights=["SEO & SEM","Google Ads","Social Media","Google Analytics 4"],
         curriculum=[
             ("Wk 1–2","SEO & Fundamentals",1), ("Wk 3–4","Google Ads",2),
             ("Wk 5–6","Social Media & Content",3), ("Wk 7–8","Analytics & Capstone",4),
         ]),
]

SERVICES = [
    dict(id=1, icon="🖥️", color="#0f766e", title="Online Live Training", tag="Most Popular", order=1,
         desc="Interactive instructor-led sessions from anywhere. Full recorded access included.",
         features=["Live interactive sessions","Recorded access 24/7","Doubt-clearing forums",
                   "Digital certificate","Online assessments"]),
    dict(id=2, icon="🏫", color="#0369a1", title="Classroom Training", tag="In-Person", order=2,
         desc="Face-to-face learning at our Accra facility. Small batches (max 15).",
         features=["Max 15 students per batch","Lab computers","Printed materials","Peer networking"]),
    dict(id=3, icon="🎯", color="#5b21b6", title="Placement Assistance", tag="95% Placed", order=3,
         desc="Our placement team works with 200+ hiring partners.",
         features=["Resume & LinkedIn review","Mock interviews","Soft skills coaching","Direct recruiter access"]),
    dict(id=4, icon="🏢", color="#b45309", title="Corporate Training", tag="Enterprise", order=4,
         desc="Custom programs for teams. We close specific skills gaps with measurable outcomes.",
         features=["Bespoke curriculum","On-site or remote","Progress dashboards","Team certifications"]),
    dict(id=5, icon="🔧", color="#0d9488", title="Real-Time Projects", tag="Hands-On", order=5,
         desc="Every course includes 3–5 production-quality projects.",
         features=["Industry project briefs","Mentor code reviews","GitHub portfolio","Demo day"]),
    dict(id=6, icon="🎓", color="#be185d", title="Certification Programs", tag="Recognised", order=6,
         desc="CodeFount certificates recognised in Ghana, Nigeria, UK and USA.",
         features=["Completion certificate","Vendor exam prep","LinkedIn badge","Alumni network"]),
]

SCHEDULES = [
    dict(id=1,  course="Cyber Security",                    date="11-Mar", time="7:30 AM"),
    dict(id=2,  course="DevOps With Multi Cloud",           date="11-Mar", time="7:00 AM"),
    dict(id=3,  course="Java Full Stack",                   date="11-Mar", time="9:00 AM"),
    dict(id=4,  course="Angular",                           date="11-Mar", time="11:00 AM"),
    dict(id=5,  course="AWS Bootcamp",                      date="06-Mar", time="6:30 AM"),
    dict(id=6,  course="Generative AI",                     date="05-Mar", time="8:00 AM"),
    dict(id=7,  course="MERN Stack",                        date="05-Mar", time="7:00 AM"),
    dict(id=8,  course="Data Analytics",                    date="05-Mar", time="7:00 AM"),
    dict(id=9,  course=".NET Core Fullstack",               date="05-Mar", time="9:00 AM"),
    dict(id=10, course="DevOps With Multi Cloud",           date="02-Mar", time="8:00 PM"),
    dict(id=11, course="JAVA Frameworks",                   date="02-Mar", time="7:30 AM"),
    dict(id=12, course="Spring Boot with Microservices",    date="02-Mar", time="7:30 AM"),
    dict(id=13, course="Python Fullstack Developer",        date="02-Mar", time="4:00 PM"),
    dict(id=14, course="Java Full Stack",                   date="27-Feb", time="11:00 AM"),
]

WORKSHOPS = [
    dict(title="Break Into Tech — Zero to Hired in 2025", facilitator="Mr. Sai",
         date="15 Mar 2025", time="10:00 AM – 1:00 PM", mode="Online (Zoom)",
         price=None, seats=80, filled=62, color="#0f766e", icon="🚀", tag="FREE",
         desc="3-hour workshop for complete beginners.",
         agenda=["Tech career landscape","Choosing your stack","Portfolio from scratch",
                 "CV and LinkedIn","Mock interview","Q&A"]),
    dict(title="Full-Stack Crash: Build a REST API in 90 Min", facilitator="Mr. Kiran",
         date="22 Mar 2025", time="9:00 AM – 10:30 AM", mode="Online (Zoom)",
         price=None, seats=60, filled=45, color="#0369a1", icon="⚡", tag="FREE",
         desc="Live coding — Node.js/Express REST API to MongoDB.",
         agenda=["Project setup","Express routes","Mongoose models","JWT auth","Postman","Deploy"]),
    dict(title="AWS Cloud Foundations Workshop", facilitator="Mr. Ashok",
         date="29 Mar 2025", time="10:00 AM – 2:00 PM", mode="Classroom (Accra)",
         price=80, seats=20, filled=14, color="#b45309", icon="☁️", tag="PAID",
         desc="Hands-on 4-hour classroom session covering AWS essentials.",
         agenda=["AWS account setup","EC2","S3","IAM","RDS","Cost management"]),
    dict(title="Introduction to Generative AI for Professionals", facilitator="Mr. Sithu",
         date="5 Apr 2025", time="2:00 PM – 5:00 PM", mode="Online (Zoom)",
         price=50, seats=100, filled=38, color="#5b21b6", icon="🤖", tag="PAID",
         desc="GenAI for your career — LLMs, chatbots and responsible AI.",
         agenda=["LLM basics","ChatGPT vs Claude","Prompt engineering","Build chatbot","Industry use-cases","Ethics"]),
    dict(title="Cyber Security Awareness for Businesses", facilitator="Mr. Dal",
         date="12 Apr 2025", time="9:00 AM – 12:00 PM", mode="Classroom (Accra)",
         price=120, seats=25, filled=10, color="#0d9488", icon="🛡️", tag="PAID",
         desc="For SME owners and non-technical staff.",
         agenda=["Phishing","Password hygiene","Remote work","Ransomware","Mobile security","Incident response"]),
    dict(title="DevOps Bootcamp: Docker & Kubernetes in a Day", facilitator="Mr. Ravi",
         date="19 Apr 2025", time="8:00 AM – 5:00 PM", mode="Hybrid",
         price=200, seats=30, filled=22, color="#7c3aed", icon="🐳", tag="PAID",
         desc="Full-day Docker to Kubernetes hands-on intensive.",
         agenda=["Docker fundamentals","Compose","Kubernetes","Pods & services","Helm","CI/CD"]),
]


async def seed(db: AsyncSession) -> None:
    from sqlalchemy import select, text

    # ── Courses ───────────────────────────────────────────────────────────────
    for c in COURSES:
        existing = (await db.execute(select(Course).where(Course.title == c["title"]))).scalar_one_or_none()
        if existing:
            continue
        curriculum_rows = c.pop("curriculum", [])
        course = Course(**c)
        db.add(course)
        await db.flush()
        for week, topic, order in curriculum_rows:
            db.add(CurriculumItem(course_id=course.id, week=week, topic=topic, order=order))
        logger.info("  ✔ Course: %s", c["title"])

    # ── Services ─────────────────────────────────────────────────────────────
    for s in SERVICES:
        existing = (await db.execute(select(Service).where(Service.title == s["title"]))).scalar_one_or_none()
        if not existing:
            db.add(Service(**s))
            logger.info("  ✔ Service: %s", s["title"])

    # ── Schedules ─────────────────────────────────────────────────────────────
    count = (await db.execute(text("SELECT COUNT(*) FROM schedules"))).scalar()
    if count == 0:
        for s in SCHEDULES:
            db.add(Schedule(**s))
        logger.info("  ✔ %d schedules seeded", len(SCHEDULES))

    # ── Workshops ─────────────────────────────────────────────────────────────
    for w in WORKSHOPS:
        existing = (await db.execute(select(Workshop).where(Workshop.title == w["title"]))).scalar_one_or_none()
        if not existing:
            db.add(Workshop(**w))
            logger.info("  ✔ Workshop: %s", w["title"])

    await db.commit()
    logger.info("✅  Seed complete")


async def main() -> None:
    logger.info("🌱  Seeding database …")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as db:
        await seed(db)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())