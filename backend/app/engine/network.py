"""Network & VPN Shield Engine.
Detects anonymizers, datacenter proxies, commercial VPNs, and Tor exit nodes.
"""
from typing import Tuple, List
from ..models.response import ReasonTag


def evaluate_network(network_type: str, ip_address: str = None) -> Tuple[int, List[ReasonTag]]:
    """
    Evaluates network telemetry:
    Returns (network_score, reason_tags).
    """
    reasons: List[ReasonTag] = []

    if network_type == "residential":
        score = 94
        reasons.append(ReasonTag(text="residential_ip_clean", type="success"))
    elif network_type == "datacenter_vpn":
        score = 40
        reasons.append(ReasonTag(text="commercial_vpn_or_datacenter_proxy", type="warning"))
    elif network_type == "tor_exit":
        score = 8
        reasons.append(ReasonTag(text="tor_anonymizing_exit_node", type="danger"))
    else:
        # Default unknown network profile
        score = 65
        reasons.append(ReasonTag(text="unclassified_asn_range", type="warning"))

    return score, reasons
