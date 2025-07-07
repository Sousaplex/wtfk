# This file makes the 'diagrams' directory a Python package.
# It also acts as a registry for all available diagram generator classes.

from .foreign_key_network import ForeignKeyNetwork
from .table_category_breakdown import TableCategoryBreakdown
from .module_dependency_graph import ModuleDependencyGraph
from .centrality_analysis_graph import CentralityAnalysisGraph
from .relationship_intensity_heatmap import RelationshipIntensityHeatmap
from .pii_sensitivity_heatmap import PiiSensitivityHeatmap
from .denormalization_heatmap import DenormalizationHeatmap
from .table_size_distribution import TableSizeDistribution
from .index_coverage_analysis import IndexCoverageAnalysis
from .performance_bottlenecks import PerformanceBottlenecks
from .orphan_and_leaf_analysis import OrphanAndLeafAnalysis
from .jsonb_usage_analysis import JsonbUsageAnalysis
from .junction_table_breakdown import JunctionTableBreakdown
from .data_type_distribution import DataTypeDistribution

DIAGRAM_REGISTRY = {
    "foreign_key_network": ForeignKeyNetwork,
    "table_category_breakdown": TableCategoryBreakdown,
    "module_dependency_graph": ModuleDependencyGraph,
    "centrality_analysis_graph": CentralityAnalysisGraph,
    "relationship_intensity_heatmap": RelationshipIntensityHeatmap,
    "pii_sensitivity_heatmap": PiiSensitivityHeatmap,
    "denormalization_heatmap": DenormalizationHeatmap,
    "table_size_distribution": TableSizeDistribution,
    "index_coverage_analysis": IndexCoverageAnalysis,
    "performance_bottlenecks": PerformanceBottlenecks,
    "orphan_and_leaf_analysis": OrphanAndLeafAnalysis,
    "jsonb_usage_analysis": JsonbUsageAnalysis,
    "junction_table_breakdown": JunctionTableBreakdown,
    "data_type_distribution": DataTypeDistribution,
}
