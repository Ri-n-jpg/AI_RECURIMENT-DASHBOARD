from django.conf import settings
from django.core.mail import EmailMessage
from django.shortcuts import get_object_or_404, render, redirect
from pypdf import PdfReader
import re

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
# EXTRACT PDF TEXT
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
# TARGET ROLES (NORMALIZED)
# -----------------------------
TARGET_ROLES = [
    "JAVA DEVELOPER",
    "BUSINESS ANALYST",
    "PROJECT MANAGER",
    "DATA ANALYST",
    "BUSINESS DEVELOPER"
]


# -----------------------------
# STATUS FUNCTION (FINAL FIX)
# -----------------------------
def get_status(score):
    if score >= 80:
        return "SHORTLISTED"
    elif score >= 50:
        return "REVIEW"
    else:
        return "REJECTED"

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
# DASHBOARD
# -----------------------------
def dashboard(request):
    candidates = Candidate.objects.all().order_by('-score', '-id')

    return render(request, "dashboard.html", {
        "candidates": candidates
    })


# -----------------------------
# GET CANDIDATES API
# -----------------------------
@api_view(["GET"])
def get_candidates(request):
    candidates = Candidate.objects.all().order_by("-id")
    serializer = CandidateSerializer(candidates, many=True)

    return Response({
        "count": candidates.count(),
        "data": serializer.data
    })


# -----------------------------
# SCORE SINGLE CANDIDATE (FIXED)
# -----------------------------
@api_view(["GET"])
def score_candidate(request, candidate_id):

    client = Groq(api_key=settings.GROQ_API_KEY)
    candidate = get_object_or_404(Candidate, id=candidate_id)

    resume_text = extract_text(candidate.resume.path)

    if not resume_text or len(resume_text) < 30:
        candidate.score = 50
        candidate.status = "REVIEW"
        candidate.save()
        return Response({"error": "Invalid resume", "score": 50})

    prompt = f"""
    You are an ATS resume scoring system.

    Analyze resume and return ONLY ONE INTEGER between 0 and 100.

    RULES:
    - No text
    - No explanation
    - No words like "score"
    - Only number

    Resume:
    {resume_text}
    """

    res = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": "Return only a number"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2
    )

    raw = res.choices[0].message.content.strip()
    print("RAW AI OUTPUT:", raw)

    match = re.search(r'\b(100|[1-9]?\d)\b', raw)

    if match:
        score = int(match.group())
    else:
        score = 50
    score = max(0, min(score, 100))

    candidate.score = score
    candidate.status = get_status(score)
    candidate.save()

    return Response({
        "candidate": candidate.name,
        "score": score,
        "status": candidate.status,
        "raw_output": raw
    })


# -----------------------------
# ADD CANDIDATE (FIXED FINAL)
# -----------------------------
def add_candidate(request):

    if request.method == "POST":

        role = request.POST.get("role", "").upper()

        candidate = Candidate.objects.create(
            name=request.POST.get("name"),
            email=request.POST.get("email"),
            role=role,
            employment_type=request.POST.get("employment_type"),
            resume=request.FILES.get("resume"),
            score=50,          # 🔥 FIX: default safe score
            status="REVIEW"
        )

        resume_text = extract_text(candidate.resume.path)

        if not resume_text or len(resume_text) < 30:
            candidate.score = 50
            candidate.status = "REVIEW"
            candidate.save()
            return redirect("/api/dashboard/")

        client = Groq(api_key=settings.GROQ_API_KEY)

        prompt = f"""
Return ONLY a number between 0 and 100.

Resume:
{resume_text}
"""

        res = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "Return only number"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )

        raw = res.choices[0].message.content.strip()
        print("RAW AI OUTPUT:", raw)

        numbers = re.findall(r'\d+', raw)

        score = int(numbers[0]) if numbers else 50
        score = max(0, min(score, 100))

        candidate.score = score
        candidate.status = get_status(score)
        candidate.save()

        return redirect("/api/dashboard/")

    return render(request, "add_candidate.html")


# -----------------------------
# PIPELINE (FINAL FIXED)
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
                c.score = 50
                c.status = "REVIEW"
                c.save()

                results.append({
                    "id": c.id,
                    "name": c.name,
                    "score": 50,
                    "status": "REVIEW",
                    "error": "Invalid resume"
                })
                continue

            prompt = f"""
Return ONLY a number between 0 and 100.

Resume:
{resume_text}
"""

            res = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}]
            )

            raw = res.choices[0].message.content.strip()

            numbers = re.findall(r'\d+', raw)

            score = int(numbers[0]) if numbers else 50
            score = max(0, min(score, 100))

            c.score = score
            c.status = get_status(score)
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

    return Response({
        "message": "Pipeline executed successfully",
        "results": results
    })


# -----------------------------
# EMAIL - TEST
# -----------------------------
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


# -----------------------------
# EMAIL - BULK
# -----------------------------
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
# ANALYZE RESUME
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
# RANK CANDIDATES
# -----------------------------
@api_view(['GET'])
def rank_candidates(request):

    candidates = Candidate.objects.all().order_by('-score', 'id')

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
# SHORTLIST
# -----------------------------
@api_view(['GET'])
def shortlist_candidates(request):

    candidates = Candidate.objects.filter(
        role__in=TARGET_ROLES,
        employment_type="C2C"
    ).order_by('-score', 'id')

    result = []

    for c in candidates:
        c.status = get_status(c.score)
        c.save()

        result.append({
            "id": c.id,
            "name": c.name,
            "score": c.score,
            "status": c.status
        })

    return Response(result)