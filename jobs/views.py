from django.conf import settings
from django.core.mail import EmailMessage
from django.shortcuts import get_object_or_404
from pypdf import PdfReader
import re
import json
from django.shortcuts import render,redirect
from rest_framework.decorators import api_view
from rest_framework.response import Response

from groq import Groq

from .models import Candidate
from .serializers import CandidateSerializer


# -----------------------------
# CLEAN TEXT
# -----------------------------
def clean_text(text):
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\x00-\x7F]+', ' ', text)
    return text.strip()


# -----------------------------
# PDF EXTRACTION
# -----------------------------
def extract_text(file_path):
    reader = PdfReader(file_path)
    text = ""

    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text

    return clean_text(text)


# -----------------------------
# TARGET ROLES
# -----------------------------
TARGET_ROLES = [
    "JAVA DEVELOPER",
    "BUSINESS ANALYST",
    "PROJECT MANAGER",
    "DATA ANALYST"
]

def dashboard(request):

    candidates = Candidate.objects.all().order_by('-score')

    return render(request, "dashboard.html", {
        "candidates": candidates
    })

# -----------------------------
# 1. GET CANDIDATES
# -----------------------------
@api_view(["GET"])
def get_candidates(request):
    candidates = Candidate.objects.all().order_by("-id")
    serializer = CandidateSerializer(candidates, many=True)

    return Response({
        "count": candidates.count(),
        "data": serializer.data
    })
@api_view(['GET'])
def send_test_email(request):

    candidate = Candidate.objects.filter(employment_type="C2C").first()

    if not candidate:
        return Response({"message": "No candidate found"})

    email = EmailMessage(
        subject=f"{candidate.role} Candidate Submission",
        body=f"""
Candidate Name: {candidate.name}
Role: {candidate.role}
Employment Type: {candidate.employment_type}

Please find attached resume.
""",
        to=["recruiter@example.com"],
        cc=["quinn@jpitstaffing.com", "kim@jpitstaffing.com"]
    )

    email.attach_file(candidate.resume.path)
    email.send()

    return Response({"message": "Email sent"})
@api_view(['GET'])
def send_bulk_email(request):

    candidates = Candidate.objects.filter(employment_type="C2C")

    count = 0

    for candidate in candidates:

        email = EmailMessage(
            subject=f"{candidate.role} Candidate Submission",
            body=f"""
Candidate Name: {candidate.name}
Role: {candidate.role}
Employment Type: {candidate.employment_type}

Please find attached resume.
""",
            to=["recruiter@example.com"],
            cc=["quinn@jpitstaffing.com", "kim@jpitstaffing.com"]
        )

        email.attach_file(candidate.resume.path)
        email.send()

        count += 1

    return Response({
        "message": f"{count} emails sent successfully"
    })

# -----------------------------
# 2. TEST AI
# -----------------------------
@api_view(['GET'])
def test_ai(request):

    client = Groq(api_key=settings.GROQ_API_KEY)

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "user", "content": "Write a 4-line summary for a Java Developer."}
        ]
    )

    return Response({
        "result": response.choices[0].message.content
    })


# -----------------------------
# 3. ANALYZE RESUME
# -----------------------------
@api_view(['GET'])
def analyze_resume(request, candidate_id):

    client = Groq(api_key=settings.GROQ_API_KEY)

    candidate = get_object_or_404(Candidate, id=candidate_id)

    resume_text = extract_text(candidate.resume.path)

    prompt = f"""
Analyze this resume:

1. Skills
2. Experience
3. Best role
4. Summary

Resume:
{resume_text}
"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}]
    )

    return Response({
        "candidate": candidate.name,
        "analysis": response.choices[0].message.content
    })


# -----------------------------
# 4. SCORE SINGLE CANDIDATE (FIXED)
# -----------------------------
@api_view(["GET"])
def score_candidate(request, candidate_id):

    client = Groq(api_key=settings.GROQ_API_KEY)

    # 1. Get candidate
    candidate = get_object_or_404(Candidate, id=candidate_id)

    # 2. Extract resume text
    resume_text = extract_text(candidate.resume.path)

    if not resume_text or len(resume_text) < 30:
        return Response({
            "error": "Invalid resume text",
            "score": 0
        })

    # 3. Strong prompt (IMPORTANT)

    prompt = f"""
    You are an ATS resume evaluator.

    Score the resume from 0 to 100 based on:

    - Skills match (0–40)
    - Projects (0–30)
    - Experience (0–20)
    - Resume clarity (0–10)

    SCORING GUIDE:
    - 80–100 = Excellent (strong skills + good projects)
    - 60–79 = Good (decent match, some experience)
    - 40–59 = Average (basic skills, limited projects)
    - 0–39 = Weak (poor match or missing skills)

    IMPORTANT RULES:
    - DO NOT give same score for all resumes
    - Analyze deeply and differentiate candidates
    - Be realistic, not biased low or high

    Return ONLY a number (0–100)

    Resume:
    {resume_text}
    """
    # 4. Call AI
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": "Return only a number 0-100."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2
    )

    raw = response.choices[0].message.content.strip()

    print("RAW AI OUTPUT:", raw)  # DEBUG (optional)

    # 5. SAFE SCORE EXTRACTION (FINAL FIX)
    match = re.search(r'\d+', raw)

    score = int(match.group()) if match else 0

    # 6. Clamp score
    score = max(0, min(score, 100))

    # 7. Save to DB
    candidate.score = score
    candidate.save()

    # 8. Response
    return Response({
        "candidate": candidate.name,
        "score": score,
        "raw_output": raw
    })
# -----------------------------
# 5. RANK CANDIDATES
# -----------------------------
@api_view(['GET'])
def rank_candidates(request):

    candidates = Candidate.objects.all().order_by('-score', 'id')

    print("=== API ORDER ===")

    for c in candidates:
        print(c.name, c.score)

    data = []
    rank = 1

    for c in candidates:
        data.append({
            "id": c.id,
            "name": c.name,
            "score": c.score,
            "rank": rank
        })
        rank += 1

    return Response(data)


# -----------------------------
# 6. SHORTLIST
# -----------------------------
@api_view(['GET'])
def shortlist_candidates(request):

    candidates = Candidate.objects.filter(
        role__in=TARGET_ROLES,
        employment_type="C2C"
    ).order_by('-score','id')

    result = []

    for c in candidates:

        if c.score >= 80:
            c.status = "SHORTLISTED"
        elif c.score >= 50:
            c.status = "REVIEW"
        else:
            c.status = "REJECTED"

        c.save()

        result.append({
            "id": c.id,
            "name": c.name,
            "score": c.score,
            "status": c.status
        })

    return Response(result)


# -----------------------------
# 7. FULL PIPELINE (FIXED)
# -----------------------------
@api_view(['GET'])
def run_pipeline(request):

    client = Groq(api_key=settings.GROQ_API_KEY)

    candidates = Candidate.objects.filter(
        role__in=TARGET_ROLES,
        employment_type="C2C"
    )

    results = []

    for c in candidates:

        try:
            resume_text = extract_text(c.resume.path)

            if not resume_text or len(resume_text) < 30:
                results.append({
                    "id": c.id,
                    "name": c.name,
                    "error": "Invalid resume"
                })
                continue

            prompt = f"""
Return ONLY a number 0-100.

Resume:
{resume_text}
"""

            res = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}]
            )

            raw = res.choices[0].message.content

            match = re.search(r'\b(100|[1-9]?\d)\b', raw)
            score = int(match.group()) if match else 0

            score = max(0, min(score, 100))

            c.score = score

            if score >= 80:
                c.status = "SHORTLISTED"
            elif score >= 50:
                c.status = "REVIEW"
            else:
                c.status = "REJECTED"

            c.save()

            results.append({
                "id": c.id,
                "name": c.name,
                "score": score,
                "status": c.status
            })

        except Exception as e:
            results.append({
                "id": c.id,
                "name": c.name,
                "error": str(e)
            })
            results = sorted(results, key=lambda x: x.get("score", 0), reverse=True)

    return Response({
        "message": "Pipeline executed successfully",
        "results": results
    })



def add_candidate(request):

    if request.method == "POST":

        # 1. Save candidate first
        candidate = Candidate.objects.create(
            name=request.POST.get("name"),
            email=request.POST.get("email"),
            role=request.POST.get("role"),
            employment_type=request.POST.get("employment_type"),
            resume=request.FILES.get("resume"),
            score=0,
            status="PENDING"
        )

        # 2. Extract resume text
        resume_text = extract_text(candidate.resume.path)

        if not resume_text:
            candidate.score = 0
            candidate.status = "REJECTED"
            candidate.save()
            return redirect("/api/dashboard/")

        # 3. AI scoring (SAME LOGIC AS score_candidate)
        client = Groq(api_key=settings.GROQ_API_KEY)

        prompt = f"""
Return ONLY valid JSON.

{{
  "score": 0-100
}}

Resume:
{resume_text}
"""

        res = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "Return only JSON"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )

        raw = res.choices[0].message.content.strip()
        print("RAW AI OUTPUT:", raw)

        try:
            data = json.loads(raw)
            score = int(data.get("score", 0))
        except:
            score = 0

        score = max(0, min(score, 100))

        # 4. Update candidate
        candidate.score = score

        if score >= 80:
            candidate.status = "SHORTLISTED"
        elif score >= 50:
            candidate.status = "REVIEW"
        else:
            candidate.status = "REJECTED"

        candidate.save()

        return redirect("/api/dashboard/")

    return render(request, "add_candidate.html")