"""Rule Registry (docs/rules.md).

새 Rule 추가 절차:
1. rules/ 에 Rule 구현체 파일 추가 (engine.Rule 구현)
2. tests/ 에 Rule 단위 테스트 (탐지/비탐지/Explainability)
3. 여기 ALL_RULES에 등록
4. docs/rules.md에 항목 추가
"""

from rules.cartesian_product import CartesianProductRule
from rules.delete_without_where import DeleteWithoutWhereRule
from rules.distinct_as_bandaid import DistinctAsBandaidRule
from rules.duplicate_join import DuplicateJoinRule
from rules.implicit_conversion import ImplicitConversionRule
from rules.join_type_mismatch import JoinTypeMismatchRule
from rules.leading_wildcard_like import LeadingWildcardLikeRule
from rules.not_in_with_null import NotInWithNullRule
from rules.null_comparison import NullComparisonRule
from rules.offset_pagination import OffsetPaginationRule
from rules.or_abuse import OrAbuseRule
from rules.pk_not_used import PkNotUsedRule
from rules.scalar_subquery_in_select import ScalarSubqueryInSelectRule
from rules.select_star import SelectStarRule
from rules.select_without_where import SelectWithoutWhereRule
from rules.union_vs_union_all import UnionVsUnionAllRule
from rules.update_without_where import UpdateWithoutWhereRule

ALL_RULES = [
    # v0.2
    CartesianProductRule(),
    DeleteWithoutWhereRule(),
    UpdateWithoutWhereRule(),
    SelectWithoutWhereRule(),
    OrAbuseRule(),
    DuplicateJoinRule(),
    SelectStarRule(),
    # v0.5 — Schema Context 필요
    PkNotUsedRule(),
    ImplicitConversionRule(),
    # v0.6
    NullComparisonRule(),
    NotInWithNullRule(),
    LeadingWildcardLikeRule(),
    ScalarSubqueryInSelectRule(),
    UnionVsUnionAllRule(),
    OffsetPaginationRule(),
    DistinctAsBandaidRule(),
    JoinTypeMismatchRule(),  # Schema Context 필요
]
