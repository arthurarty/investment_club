from django.contrib import admin

from clubs.models import (
    Club,
    ClubMember,
    FinancialTransaction,
    FinancialYear,
    FinancialYearContribution,
    FinancialYearParticipant,
    IndividualDue,
)

admin.site.register(Club)
admin.site.register(ClubMember)
admin.site.register(FinancialYear)
admin.site.register(FinancialYearParticipant)
admin.site.register(FinancialTransaction)
admin.site.register(FinancialYearContribution)
admin.site.register(IndividualDue)
