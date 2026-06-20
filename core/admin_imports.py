# ============================================================================
# ELITE CONSTRUCTION ADMIN PANEL
# BEAUTIFUL • MODERN • POWERFUL
# Keeps your existing logic intact while upgrading design, UX, readability
# ============================================================================

from decimal import Decimal
from datetime import datetime

from django.contrib import admin, messages
from django.contrib.auth.models import User
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html

from .models import (
    UserProfile,
    Project,
    BOQItem,
    DailyLog,
    DailyLogEntry,
    ProjectAssignment,
    InspectionPoint,
    InspectionRecord,
    ApprovalLevel,
    ApprovalRecord,
    RFI,
    ChangeOrder,
    MaterialSubmittal,
    Invoice,
    InvoiceItem,
)
