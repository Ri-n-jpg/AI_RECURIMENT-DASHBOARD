from django.urls import path
from .views import (
    get_candidates,
    send_test_email,
    send_bulk_email,
    test_ai,
    analyze_resume,
    score_candidate,
    rank_candidates,
    shortlist_candidates,
    run_pipeline,
    dashboard,
add_candidate,
)

urlpatterns = [
    path('candidates/', get_candidates),

    path('send-email/', send_test_email),
    path('send-bulk-email/', send_bulk_email),

    path('test-ai/', test_ai),

    path('analyze-resume/<int:candidate_id>/', analyze_resume),

    path('score/<int:candidate_id>/', score_candidate),


    path('rank/', rank_candidates),

    path('shortlist/', shortlist_candidates),

    path('run-pipeline/', run_pipeline),
path('dashboard/', dashboard, name='dashboard'),
path('add-candidate/', add_candidate, name='add_candidate'),
]