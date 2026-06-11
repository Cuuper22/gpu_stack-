"""
gpu_stack.presets.dgx_h100_tco
================================

DGX H100 node-level power bill-of-materials (sourced) and full TCO
closure (assumption) presets needed to resolve econ.cost.per_token for
the pythia_70m_dgx_h100_us_2024_industrial_power scenario pack.

Two layers are separated so callers can identify which numbers are
public hardware facts and which are scenario-layer assumptions:

  dgx_h100_node_power_bom
    Sourced power roots for the DGX H100 node from Intel and NVIDIA
    public datasheets. Covers CPU socket TDP, ConnectX-7 NIC card
    power, and local NVMe SSD count and per-drive power.

  pythia_70m_dgx_h100_run_closure_assumption
    Assumption-labeled economic and thermal closure pack. Covers all
    remaining root inputs needed to close econ.cost.per_token for a
    single DGX H100 single-node scenario: RAM power coefficient, node
    misc power, asset lifecycle, hardware capex (GPU, CPU, DRAM, NIC,
    storage, chassis, rack, cluster), utilization, facility capex
    inputs, maintenance, staff, network transit, demand charge, water,
    carbon intensity and price, and cooling-tower thermal parameters.
    Each assumption is labeled with its rationale and bound.
"""

from __future__ import annotations

from ..core.presets import Preset
from ..core.registry import Registry


def _root_assignments(assignments: dict[str, float]) -> dict[str, float]:
    unknown = [name for name in assignments if name not in Registry.variables]
    if unknown:
        raise ValueError(
            "dgx_h100_tco preset assignments reference unknown variables: "
            f"{sorted(unknown)}"
        )
    non_roots = [
        name
        for name in assignments
        if not Registry.variables[name].is_root_input
    ]
    if non_roots:
        raise ValueError(
            "dgx_h100_tco preset assignments must be root inputs only: "
            f"{sorted(non_roots)}"
        )
    return assignments


# ---------------------------------------------------------------------------
# Source strings
# ---------------------------------------------------------------------------

_INTEL_8480C_SOURCE = (
    "Intel Xeon Platinum 8480C Processor (105M Cache, 2.00 GHz) product "
    "specifications, https://www.intel.com/content/www/us/en/products/sku/"
    "231730/intel-xeon-platinum-8480c-processor-105m-cache-2-00-ghz/"
    "specifications.html (accessed 2026-06-10): TDP = 350 W."
)

_CONNECTX7_SOURCE = (
    "NVIDIA ConnectX-7 adapter card specifications, "
    "https://networking-docs.nvidia.com/connectx7hw/specifications "
    "(accessed 2026-06-10): MCX75310AAS-NEAT (single-port OSFP) typical "
    "power with passive cables in PCIe Gen 5.0 x16 = 24.9 W. This figure "
    "covers the card including on-board PHY logic; port-facing optic or "
    "retimer power is assigned separately to cluster.node.nic.power_per_port."
)

_DGX_H100_STORAGE_SOURCE = (
    "NVIDIA DGX H100/H200 User Guide, Introduction to NVIDIA DGX H100/H200 "
    "Systems, https://docs.nvidia.com/dgx/dgxh100-user-guide/"
    "introduction-to-dgxh100.html (accessed 2026-06-10): local storage is "
    "8 x 3.84 TB NVMe U.2 SEDs in RAID 0 plus 2 x 1.92 TB NVMe M.2 SSDs "
    "in RAID 1 for the OS. The power model assigns the 8 data-cache U.2 "
    "drives. Enterprise U.2 NVMe SSD active power reference: Samsung PM9A3 "
    "and similar enterprise U.2 NVMe drives are rated 8-11 W active; "
    "Samsung PM983/983 DCT datasheet lists 8.7 W active read, 10.6 W active "
    "write, 4 W idle. This preset uses 9.0 W per drive as a representative "
    "active-operation value within the published 8-11 W range."
)

# ---------------------------------------------------------------------------
# Sourced power bill-of-materials for the DGX H100 node
# ---------------------------------------------------------------------------

dgx_h100_node_power_bom = Preset(
    name="dgx_h100_node_power_bom",
    description=(
        "Sourced power bill-of-materials for the NVIDIA DGX H100 node: "
        "Intel Xeon Platinum 8480C CPU socket TDP, NVIDIA ConnectX-7 "
        "single-port NIC card typical power, and local U.2 NVMe SSD "
        "count and per-drive active power."
    ),
    assignments=_root_assignments({
        # Intel Xeon Platinum 8480C TDP = 350 W per socket.
        "cluster.node.cpu.power_per_cpu": 350.0,
        # ConnectX-7 MCX75310AAS-NEAT single-port OSFP typical power
        # with passive cables = 24.9 W. The DGX H100 has 8 x ConnectX-7
        # single-port InfiniBand cards. This assignment captures the card
        # board power; InfiniBand active-optical cable transceiver or
        # copper-direct-attach retimer overhead is not included because
        # the cited specification uses passive cables.
        "cluster.node.nic.power_per_nic": 24.9,
        # Per-port overhead above the card board power. The cited 24.9 W
        # figure already covers internal PHY logic. Active optics or
        # retimer power is a scenario-layer assumption captured separately
        # in the closure pack. Set to zero here: the sourced spec bundles
        # port-facing logic into the card total.
        "cluster.node.nic.power_per_port": 0.0,
        # 8 x 3.84 TB U.2 NVMe SED data-cache drives per DGX H100 node.
        "cluster.node.local_ssd.count": 8.0,
        # Enterprise U.2 NVMe SSD active power: 9.0 W per drive,
        # within the published 8.7-10.6 W range for Samsung PM983/DCT.
        "cluster.node.local_ssd.power_per_drive": 9.0,
    }),
    source=(
        f"{_INTEL_8480C_SOURCE} | {_CONNECTX7_SOURCE} | {_DGX_H100_STORAGE_SOURCE}"
    ),
    notes=(
        "cluster.node.cpu.power_per_cpu=350 W is the Intel-published TDP "
        "for the Xeon Platinum 8480C. Actual socket power under AI workloads "
        "can differ from TDP; TDP is the thermal design boundary used here.",
        "cluster.node.nic.power_per_nic=24.9 W is specified for passive "
        "direct-attach copper cables. InfiniBand active-optical cable "
        "transceivers can add 8-9 W per port; that increment should be "
        "captured in cluster.node.nic.power_per_port or in a separate "
        "assumption layer if active optics are modeled.",
        "cluster.node.nic.power_per_port=0.0 treats port-facing overhead "
        "as already included in the 24.9 W card figure for the passive-cable "
        "case. Override for active optic deployments.",
        "cluster.node.local_ssd.count=8 assigns the eight U.2 cache drives. "
        "The two M.2 OS drives are excluded because they run in RAID 1 "
        "with minimal AI-workload I/O and their power is subsumed in the "
        "misc_fixed_power assumption closure.",
        "cluster.node.local_ssd.power_per_drive=9.0 W is a sourced estimate "
        "for enterprise U.2 NVMe drives at sustained active operation, "
        "within the Samsung PM983 DCT published range.",
    ),
)


# ---------------------------------------------------------------------------
# Assumption-labeled economic and thermal closure pack
# ---------------------------------------------------------------------------

_ASSUMPTION_PREFIX = (
    "Scenario-layer assumption for the pythia_70m_dgx_h100 single-node "
    "TCO closure. "
)

_WATER_PHYSICS_SOURCE = (
    "Water latent heat of vaporization at 20 degC: 2454 kJ/kg (standard "
    "thermophysics reference, NIST Chemistry WebBook SRD 69, "
    "https://webbook.nist.gov/chemistry/fluid/ (accessed 2026-06-10), "
    "Water saturation properties). Water density at 20 degC: 0.998 kg/L "
    "(NIST, same source). Cooling tower drift: 0.001 to 0.005 of evaporation "
    "mass flow (U.S. Department of Energy, Best Management Practice 10: "
    "Cooling Tower Management, "
    "https://www.energy.gov/cmei/femp/best-management-practice-10-cooling-"
    "tower-management (accessed 2026-06-10)). Cycles of concentration: "
    "typical 3-5 for chemical inhibitor programs (DOE, same source)."
)

pythia_70m_dgx_h100_run_closure_assumption = Preset(
    name="pythia_70m_dgx_h100_run_closure_assumption",
    description=(
        "Assumption-labeled TCO and thermal closure pack for the Pythia-70M "
        "on a single DGX H100 node. Supplies all remaining root inputs needed "
        "to resolve econ.cost.per_token beyond the sourced hardware, workload, "
        "electricity-price, and DGX H100 power-BOM presets. All values are "
        "explicitly scenario-layer assumptions, not measured procurement or "
        "site-specific data."
    ),
    assignments=_root_assignments({
        # -----------------------------------------------------------------------
        # RAM power
        # -----------------------------------------------------------------------
        # DGX H100 has 2 TB CPU-side DRAM = 32 x 64 GB DDR5 RDIMMs.
        # DDR5 64 GB RDIMM typical power at server workloads:
        # ~ 8-12 W per DIMM (a 0.3 W/GB proxy for DDR5 at moderate load,
        # consistent with DDR4 reference of 3 W/8 GB ~ 0.375 W/GB, scaled
        # down 20% for DDR5). Using 10 W per 64 GB DIMM -> 0.3125 W/GB
        # -> 1.5625e-10 W/byte. Range: 0.25 W/GB (idle) to 0.5 W/GB (peak).
        "cluster.node.ram.power_per_byte": 1.5625e-10,
        # -----------------------------------------------------------------------
        # Node misc power
        # -----------------------------------------------------------------------
        # Fixed chassis/BMC/motherboard/fan overhead for an 8-GPU DGX-class
        # system. Typical chassis management, fans, VRMs, and motherboard
        # draw for large server systems: 150-250 W. Using 200 W as midpoint.
        "cluster.node.misc.fixed_power": 200.0,
        # Per-GPU slot, riser, and cabling overhead. DGX H100 uses NVLink
        # interconnect; PCIe riser and power-rail overhead per GPU slot is
        # approximately 25-50 W. Using 25 W per GPU slot.
        "cluster.node.misc.power_per_gpu": 25.0,
        # -----------------------------------------------------------------------
        # GPU and asset capex
        # -----------------------------------------------------------------------
        # H100 SXM GPU procured price in 2024 datacenter channel:
        # market range $27,000-$40,000 per card. Using $30,000 as a
        # mid-range 2024 reference point. This is not NVIDIA MSRP (not
        # published); it is a channel-market scenario boundary.
        "econ.gpu.capex": 30_000.0,
        # Depreciation horizon: 4 years = 4 * 365.25 * 86400 s.
        # GPU and datacenter IT equipment commonly depreciated over 3-5
        # years. Using 4 years as a standard IT asset lifecycle assumption.
        "econ.asset.useful_life": 126_230_400.0,  # 4 * 365.25 * 86400
        # Residual value fraction at end of depreciation: 5 %.
        # Used equipment typically retains some residual value.
        "econ.asset.residual_fraction": 0.05,
        # -----------------------------------------------------------------------
        # Node sub-component capex
        # -----------------------------------------------------------------------
        # Dual Intel Xeon Platinum 8480C CPUs: OEM/tray price ~$4,000-$7,000
        # per CPU in 2024 channel. Using $5,000 per CPU, two CPUs -> $10,000.
        # Assigned per-node.
        "econ.node.cpu_capex": 10_000.0,
        # 2 TB DDR5 RDIMM (32 x 64 GB): DDR5 64 GB RDIMM OEM 2024 price
        # approximately $200-$350. Using $250 per DIMM, 32 DIMMs -> $8,000.
        "econ.node.dram_capex": 8_000.0,
        # 8 x ConnectX-7 single-port InfiniBand NICs: OEM 2024 price
        # approximately $500-$1,000 per card plus cables. Using $700 per
        # card all-in, 8 cards -> $5,600.
        "econ.node.nic_capex": 5_600.0,
        # 8 x 3.84 TB U.2 NVMe SED drives: enterprise U.2 NVMe 3.84 TB
        # approximately $500-$1,000 per drive in 2024. Using $600 per drive,
        # 8 drives -> $4,800.
        "econ.node.storage_capex": 4_800.0,
        # DGX H100 chassis, motherboard, PSU, and assembly. Estimated
        # $10,000-$20,000 for the non-GPU, non-CPU, non-DRAM platform.
        # Using $15,000 per node.
        "econ.node.chassis_capex": 15_000.0,
        # -----------------------------------------------------------------------
        # Rack-level capex
        # -----------------------------------------------------------------------
        # Top-of-rack switch per rack: 1U/2U 400G ToR switch $5,000-$20,000.
        # For a single-node scenario there is one rack with one node.
        # Using $10,000 per rack.
        "econ.rack.switch_capex": 10_000.0,
        # Rack PDU (power distribution unit): $2,000-$5,000. Using $3,000.
        "econ.rack.power_distribution_capex": 3_000.0,
        # -----------------------------------------------------------------------
        # Cluster-level capex
        # -----------------------------------------------------------------------
        # Spine network: for a single-node scenario with one rack,
        # spine fabric is minimal. Using $5,000 as a nominal single-rack
        # spine interconnect boundary.
        "econ.cluster.spine_network_capex": 5_000.0,
        # Shared storage (parallel filesystem): a small NFS/Lustre
        # appliance for a single-node scenario. Using $20,000.
        "econ.cluster.storage_capex": 20_000.0,
        # Cluster utilization: fraction of time productively used.
        # A dedicated single-node research cluster running a training job
        # continuously. Using 0.90 (90 %) as a high-utilization research
        # boundary assumption.
        "econ.cluster.utilization": 0.90,
        # -----------------------------------------------------------------------
        # Facility capex inputs
        # -----------------------------------------------------------------------
        # Building shell unit cost: $800/m^2 is representative of
        # US industrial/data center shell construction in 2024.
        # (Cushman & Wakefield Data Center Development Cost Guide 2024:
        # $600-$1,100/sqft x 0.093 m^2/sqft ~ $56-$102/sqft range maps to
        # roughly $600-$1,100/m^2; using $800/m^2 as midpoint.)
        "econ.facility.building_shell_unit_cost": 800.0,
        # Power infrastructure unit cost: $1.5/W for utility service,
        # switchgear, UPS, generators, and transformers.
        # (Industry reference: $10M/MW = $10/W for full facility, of which
        # electrical systems are roughly $280-$460/sqft of ~$900/sqft total.
        # Electrical fraction ~0.38 of $10/W ~ $3.8/W. For a single-node
        # pilot with lighter infrastructure: $1.50/W assumption.)
        "econ.facility.power_infra_unit_cost": 1.50,
        # Cooling infrastructure unit cost: $1.0/W for CDU, chillers,
        # cooling tower, and distribution plumbing. Single-node scale.
        "econ.facility.cooling_infra_unit_cost": 1.00,
        # Floor area: DGX H100 occupies a 10 kW/m^2 density rack in a
        # 1-rack colocation space; a minimal facility footprint of 10 m^2
        # covers the rack, aisle, and immediate support area.
        "thermal.facility.floor_area": 10.0,
        # Electrical design capacity: one DGX H100 node at 10.2 kW max plus
        # 20 % overhead for PDU, UPS, and cooling plant margin -> 12.24 kW.
        # Rounding to 15,000 W (15 kW) to capture facility headroom.
        "thermal.facility.power_design_capacity": 15_000.0,
        # Cooling design capacity: matched to electrical design capacity for
        # a PUE ~ 1.0 colocation scenario. Using same 15,000 W.
        "thermal.facility.cooling_design_capacity": 15_000.0,
        # -----------------------------------------------------------------------
        # Maintenance
        # -----------------------------------------------------------------------
        # Annual maintenance fraction: 2 % of total capex per year.
        # Typical enterprise IT maintenance contracts: 1-3 %. Using 2 %.
        # Units: 1/year (the model converts to 1/s internally).
        "econ.maintenance.fraction_per_year": 0.02,
        # -----------------------------------------------------------------------
        # Staff
        # -----------------------------------------------------------------------
        # Staff cost rate: one 0.25 FTE datacenter operator allocated to
        # the single-node facility, at $120,000/year fully-loaded cost.
        # 0.25 FTE * $120,000/yr = $30,000/yr = $30,000/(365.25*86400) s.
        "econ.staff.cost_rate": 9.506e-4,   # 30000 / 31_557_600
        # -----------------------------------------------------------------------
        # Network transit
        # -----------------------------------------------------------------------
        # Network transit price: $0.08/GB is a common US cloud egress price.
        # For a self-hosted single-node scenario this represents minimal
        # external egress cost. 0.08 USD/GB = 0.08/1e9 USD/byte.
        "econ.network.transit_price_per_gb": 0.08,
        # Egress bandwidth: for a training-only single-node run, external
        # egress is minimal. Using 1 MB/s = 1e6 byte/s as a nominal
        # boundary for checkpoint sync / monitoring traffic.
        "econ.network.egress_bytes_per_s": 1e6,
        # -----------------------------------------------------------------------
        # Power demand charge
        # -----------------------------------------------------------------------
        # Capacity charge per kW-month: $8.00/(kW*month) is a common US
        # industrial demand-charge rate. Demand charges vary widely;
        # $5-$15/kW-month is a representative US industrial range.
        "econ.power.capacity_charge_kw_month": 8.00,
        # -----------------------------------------------------------------------
        # Water cost
        # -----------------------------------------------------------------------
        # Water price: $0.005/L = $5/m^3 is representative of US municipal
        # industrial water rates including treatment and discharge.
        # (U.S. average industrial water cost approximately $1-$10/m^3.)
        "econ.water.price_per_liter": 0.005,
        # -----------------------------------------------------------------------
        # Carbon
        # -----------------------------------------------------------------------
        # Grid carbon intensity: U.S. national average 2022-2023 from EPA
        # eGRID: approximately 386 g CO2/kWh = 0.386 kg/(kW*h).
        # Source: EPA eGRID2023 national output emission rate ~386 g CO2/kWh,
        # https://www.epa.gov/egrid (released January 2025; 2023 data).
        "econ.carbon.intensity_kg_per_kwh": 0.386,
        # Carbon price: $0.0 per tonne (no carbon tax or offset requirement
        # assumed for this scenario). The econ.carbon.cost_rate term drops
        # to zero, leaving CO2 emissions calculated but not priced. Override
        # to model carbon pricing scenarios.
        "econ.carbon.price_per_tonne": 0.0,
        # -----------------------------------------------------------------------
        # Cooling-tower thermal parameters
        # -----------------------------------------------------------------------
        # Latent heat of vaporization of water at 20 degC: 2454 kJ/kg.
        # Source: NIST Chemistry WebBook SRD 69 water saturation properties.
        "thermal.water.latent_heat": 2_454_000.0,  # J/kg
        # Water density at 20 degC: 0.998 kg/L.
        # Source: NIST Chemistry WebBook SRD 69.
        "thermal.water.density": 0.998,  # kg/L
        # Cycles of concentration: 4.5, within the 3-8 range for
        # well-managed cooling towers with chemical inhibitor programs.
        # Source: DOE FEMP Best Management Practice 10 reference range 3-8.
        "thermal.water.cycles_of_concentration": 4.5,
        # Tower drift fraction: 0.002 (0.2 % of evaporated water mass),
        # within the published 0.001-0.005 range.
        "thermal.water.drift_fraction": 0.002,
        # -----------------------------------------------------------------------
        # Facility heat reuse
        # -----------------------------------------------------------------------
        # Heat reuse fraction: 0.0 (no heat reuse for this baseline scenario).
        # Most US datacenters do not recover waste heat; 0.0 is the conservative
        # baseline. Override to model district heating or CHP scenarios.
        "thermal.facility.heat_reuse_fraction": 0.0,
    }),
    source=(
        "Scenario-layer assumption closure for pythia_70m_dgx_h100 single-node "
        "TCO. RAM power: DDR5 10 W per 64 GB RDIMM assumption consistent with "
        "20 % reduction vs DDR4 rule-of-thumb (0.375 W/GB -> 0.3125 W/GB). "
        "Misc node power: industry-typical 150-250 W chassis overhead and "
        "25 W per GPU slot assumption for DGX-class systems. GPU capex: "
        "2024 channel market range $27,000-$40,000 per H100 SXM card "
        "(IntuitionLabs NVIDIA AI GPU Pricing Guide, "
        "https://intuitionlabs.ai/articles/nvidia-ai-gpu-pricing-guide, "
        "accessed 2026-06-10); $30,000 per GPU used as mid-range scenario "
        "boundary. Asset lifecycle: 4-year IT depreciation, 5 % residual "
        "value: standard enterprise IT accounting assumption. Sub-component "
        "capex (CPU, DRAM, NIC, storage, chassis, rack, cluster): 2024 OEM "
        "channel price estimates within published market ranges; individual "
        "entries labeled in notes. Facility capex inputs: Cushman and Wakefield "
        "US Data Center Development Cost Guide 2024 ranges for shell and "
        "infrastructure unit costs; single-node facility footprint. Carbon "
        "intensity: EPA eGRID2023 national average approximately 386 g CO2/kWh, "
        "https://www.epa.gov/egrid (EPA eGRID2023, released January 2025). "
        "Carbon price: zero (no carbon tax modeled in this baseline scenario). "
        "Cooling-tower water properties: NIST Chemistry WebBook SRD 69 "
        "(https://webbook.nist.gov/chemistry/fluid/, accessed 2026-06-10) "
        "for latent heat and density. Tower drift and cycles of concentration: "
        "DOE FEMP Best Management Practice 10, "
        "https://www.energy.gov/cmei/femp/"
        "best-management-practice-10-cooling-tower-management "
        "(accessed 2026-06-10). Utilization: 0.90 high-utilization "
        "research-node assumption. Staff: 0.25 FTE at $120,000/yr "
        "fully-loaded cost assumption."
    ),
    notes=(
        "cluster.node.ram.power_per_byte=1.5625e-10 W/byte represents "
        "10 W per 64 GB RDIMM. DDR5 typical power varies 8-15 W per module "
        "depending on speed and load. Override for measured DRAM power data.",
        "cluster.node.misc.fixed_power=200 W covers BMC, VRMs, motherboard, "
        "and fan power. DGX H100 system-level overhead beyond named components "
        "is estimated; actual fan power varies with workload and ambient.",
        "cluster.node.misc.power_per_gpu=25 W per GPU slot covers PCIe "
        "riser, cabling, and power-rail overhead. Override with measured "
        "slot-level power draw.",
        "econ.gpu.capex=30000 USD is a 2024 channel-market mid-range "
        "scenario boundary, not a listed price. H100 SXM channel prices "
        "ranged $27,000-$40,000 depending on vendor and timing.",
        "econ.asset.useful_life=126230400 s encodes a 4-year depreciation "
        "horizon (4 * 365.25 * 86400 s). Standard IT lifecycle assumption.",
        "econ.asset.residual_fraction=0.05 sets a 5 % terminal residual "
        "value. Actual GPU secondary-market values vary widely.",
        "econ.node.cpu_capex=10000 USD covers two Intel Xeon Platinum 8480C "
        "CPUs at $5,000 each (2024 OEM tray channel estimate).",
        "econ.node.dram_capex=8000 USD covers 32 x 64 GB DDR5 RDIMMs at "
        "$250 each (2024 OEM channel estimate).",
        "econ.node.nic_capex=5600 USD covers 8 x ConnectX-7 cards with "
        "cables at $700 each (2024 OEM channel estimate).",
        "econ.node.storage_capex=4800 USD covers 8 x 3.84 TB U.2 NVMe "
        "SEDs at $600 each (2024 OEM channel estimate).",
        "econ.node.chassis_capex=15000 USD covers DGX H100 chassis, "
        "motherboard, six 3.3 kW PSUs, and assembly. Estimate only.",
        "econ.cluster.utilization=0.90 assumes the node runs productive "
        "workloads 90 % of the time. Adjust for shared or idle-heavy nodes.",
        "econ.carbon.intensity_kg_per_kwh=0.386 uses the EPA eGRID2023 "
        "national average output rate (approximately 386 g CO2/kWh). "
        "Regional intensity can differ substantially.",
        "econ.carbon.price_per_tonne=0.0 disables carbon cost. Override "
        "with a voluntary or compliance carbon price (e.g. $50-$200/tonne "
        "for US scenarios).",
        "thermal.water.latent_heat=2454000 J/kg and thermal.water.density="
        "0.998 kg/L are physical properties of water at 20 degC from NIST.",
        "thermal.water.cycles_of_concentration=4.5 and "
        "thermal.water.drift_fraction=0.002 are middle-of-range values "
        "for well-managed cooling towers.",
        "thermal.facility.heat_reuse_fraction=0.0 models no waste-heat "
        "recovery. Override for district heating scenarios.",
        "Facility capex inputs represent single-node colocation-class "
        "infrastructure at a 15 kW electrical design capacity.",
        "Staff cost assignment: 0.25 FTE * $120,000/yr / 31,557,600 s/yr "
        "= $9.506e-4 USD/s.",
        "econ.network.transit_price_per_gb=0.08 USD/GB and "
        "econ.network.egress_bytes_per_s=1e6 byte/s give a minimal "
        "transit cost boundary for a single-node on-premises system.",
        "econ.power.capacity_charge_kw_month=8.00 USD/(kW*month) is "
        "a representative US industrial demand charge; actual rates vary.",
        "econ.water.price_per_liter=0.005 USD/L ($5/m^3) represents "
        "US industrial water cost including treatment and discharge.",
        "This pack is an explicit assumption closure, not measured "
        "procurement, staffing, or site-specific data.",
    ),
)


__all__ = [
    "dgx_h100_node_power_bom",
    "pythia_70m_dgx_h100_run_closure_assumption",
]
