from django.contrib import admin

from clubs.models import (
    Club,
    ClubMembership,
    FinancialTransaction,
    FinancialYear,
    FinancialYearContribution,
    FinancialYearParticipant,
    IndividualDue,
    TransactionCategory,
)

admin.site.register(Club)
admin.site.register(ClubMembership)
admin.site.register(FinancialYear)
admin.site.register(FinancialYearParticipant)
admin.site.register(FinancialTransaction)
admin.site.register(FinancialYearContribution)
admin.site.register(IndividualDue)
admin.site.register(TransactionCategory)
