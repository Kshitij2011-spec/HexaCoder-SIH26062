"""Deterministic Personnel & Field Team Deployment Safety Engine (Milestone A10).

Evaluates operational personnel deployment readiness and safety compliance
using only authoritative repository fields and relationships.
Strictly decision-support and advisory; performs zero autonomous mutations.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Set
from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.app.domains.people.models import PersonModel
from backend.app.domains.teams.models import TeamModel
from backend.app.domains.missions.models import MissionModel
from backend.app.domains.locations.models import LocationModel
from backend.app.domains.control_tower.schemas import (
    PersonnelSafetyFinding,
    TeamDeploymentPosture,
    PersonnelPostureSummary,
)
from backend.app.core.errors import EntityNotFoundError


class PersonnelSafetyService:
    """
    Deterministic domain service evaluating personnel deployment safety
    and field team qualification compliance across an expedition campaign.
    """

    def __init__(self, session: Session):
        self.session = session

    def evaluate_expedition(self, expedition_id: uuid.UUID) -> PersonnelPostureSummary:
        """
        Evaluates campaign personnel safety posture against strict deterministic rules:
        1. PERS_READINESS_DISQUALIFIED: checks for medical hold or unavailable members.
        2. PERS_MOVEMENT_INCOMPATIBLE: checks for movement state incompatible with mission.
        3. TEAM_HEADCOUNT_DEFICIT: enforces mandatory polar 2-person buddy safety floor.
        4. TEAM_LEADER_UNREADY: verifies certified ready team leadership.
        5. FIELD_SAFETY_OFFICER_ABSENT: validates certified safety officer / guide presence.
        """
        now = datetime.now(timezone.utc)

        # 1. Fetch all people for expedition
        people_stmt = (
            select(PersonModel)
            .where(PersonModel.expedition_id == expedition_id)
            .order_by(PersonModel.person_code.asc())
        )
        people = list(self.session.execute(people_stmt).scalars().all())

        # 2. Fetch all teams for expedition
        teams_stmt = (
            select(TeamModel)
            .where(TeamModel.expedition_id == expedition_id)
            .order_by(TeamModel.code.asc())
        )
        teams = list(self.session.execute(teams_stmt).scalars().all())

        # 3. Fetch all missions for expedition
        missions_stmt = select(MissionModel).where(MissionModel.expedition_id == expedition_id)
        missions = list(self.session.execute(missions_stmt).scalars().all())
        missions_by_id = {m.id: m for m in missions}

        # 4. Fetch locations for name mapping
        locations_stmt = select(LocationModel)
        locations = list(self.session.execute(locations_stmt).scalars().all())
        locations_by_id = {loc.id: loc for loc in locations}

        # 5. Aggregate personnel stats
        total_personnel = len(people)
        cleared_count = sum(1 for p in people if p.readiness_state == "READY")
        medical_hold_count = sum(1 for p in people if p.readiness_state in ("NOT_CLEARED", "CLEARANCE_PENDING"))
        unavailable_count = sum(1 for p in people if p.readiness_state == "UNAVAILABLE")
        at_station_count = sum(1 for p in people if p.movement_state == "AT_STATION")
        field_deployed_count = sum(1 for p in people if p.movement_state in ("FIELD", "FIELD_DEPLOYED"))
        in_transit_count = sum(1 for p in people if p.movement_state in ("IN_TRANSIT", "RETURNING"))

        # Map people by ID and team
        people_by_id = {p.id: p for p in people}
        team_members_map: Dict[uuid.UUID, List[PersonModel]] = {t.id: [] for t in teams}
        for p in people:
            if p.team_id and p.team_id in team_members_map:
                team_members_map[p.team_id].append(p)

        # Candidate pool for reassignments: cleared personnel at station base
        station_candidates = [
            p for p in people
            if p.readiness_state == "READY" and p.movement_state in ("AT_STATION", "NOT_DEPLOYED")
        ]

        findings: List[PersonnelSafetyFinding] = []
        team_postures: List[TeamDeploymentPosture] = []
        reassignment_opportunities: List[Dict[str, Any]] = []

        # 6. Evaluate each team against deterministic rules
        for team in teams:
            members = team_members_map.get(team.id, [])
            mission = missions_by_id.get(team.mission_id) if team.mission_id else None
            leader = people_by_id.get(team.leader_person_id) if team.leader_person_id else None
            loc = locations_by_id.get(team.location_id) if team.location_id else None

            team_findings: List[PersonnelSafetyFinding] = []
            unmet_requirements: List[str] = []

            # Rule 1: Disqualified or unready members
            disqualified_members = [
                m for m in members
                if m.readiness_state in ("NOT_CLEARED", "UNAVAILABLE")
            ]
            for dm in disqualified_members:
                f_item = PersonnelSafetyFinding(
                    finding_id=f"FINDING-READINESS-{dm.person_code}-{team.code}",
                    rule_id="PERS_READINESS_DISQUALIFIED",
                    status="BLOCKED",
                    subject_type="PERSON",
                    subject_id=dm.id,
                    subject_code=dm.person_code,
                    subject_name=dm.full_name,
                    mission_id=mission.id if mission else None,
                    mission_code=mission.code if mission else None,
                    team_id=team.id,
                    team_code=team.code,
                    reason=(
                        f"Personnel member '{dm.person_code}' ({dm.full_name}) is in disqualifying readiness "
                        f"state '{dm.readiness_state}' while assigned to team '{team.code}'."
                    ),
                    evidence={
                        "person_code": dm.person_code,
                        "readiness_state": dm.readiness_state,
                        "role": dm.role,
                        "team_code": team.code,
                        "mission_code": mission.code if mission else None,
                    },
                    recommended_action=(
                        f"Initiate operational replanning to substitute '{dm.person_code}' with an available "
                        f"cleared specialist from the station complement."
                    ),
                    data_provenance="DERIVED",
                )
                team_findings.append(f_item)
                unmet_requirements.append(
                    f"Disqualified member '{dm.person_code}' ({dm.readiness_state}) requires substitution"
                )

                # Identify potential replacement candidates from station complement
                eligible_replacements = [
                    cand for cand in station_candidates
                    if cand.id != dm.id and cand.team_id != team.id
                ]
                for er in eligible_replacements[:2]:
                    reassignment_opportunities.append({
                        "team_id": str(team.id),
                        "team_code": team.code,
                        "mission_id": str(mission.id) if mission else None,
                        "mission_code": mission.code if mission else None,
                        "displaced_person_id": str(dm.id),
                        "displaced_person_code": dm.person_code,
                        "displaced_role": dm.role,
                        "candidate_person_id": str(er.id),
                        "candidate_person_code": er.person_code,
                        "candidate_full_name": er.full_name,
                        "candidate_role": er.role,
                        "candidate_readiness": er.readiness_state,
                        "rationale": (
                            f"Substitute disqualified {dm.person_code} with cleared station personnel "
                            f"{er.person_code} ({er.full_name}, {er.role})."
                        ),
                        "data_provenance": "ADVISORY",
                    })

            # Rule 2: Movement state incompatible with deployment
            if team.status in ("FIELD", "DEPLOYED"):
                incompatible_movement = [
                    m for m in members
                    if m.movement_state in ("NOT_DEPLOYED", "RETURNING", "RETURNED")
                ]
                for im in incompatible_movement:
                    f_item = PersonnelSafetyFinding(
                        finding_id=f"FINDING-MOVEMENT-{im.person_code}-{team.code}",
                        rule_id="PERS_MOVEMENT_INCOMPATIBLE",
                        status="BLOCKED",
                        subject_type="PERSON",
                        subject_id=im.id,
                        subject_code=im.person_code,
                        subject_name=im.full_name,
                        mission_id=mission.id if mission else None,
                        mission_code=mission.code if mission else None,
                        team_id=team.id,
                        team_code=team.code,
                        reason=(
                            f"Personnel member '{im.person_code}' ({im.full_name}) has movement state "
                            f"'{im.movement_state}', incompatible with active field deployment '{team.code}'."
                        ),
                        evidence={
                            "person_code": im.person_code,
                            "movement_state": im.movement_state,
                            "team_status": team.status,
                        },
                        recommended_action="Update personnel movement transit log or reassign local team member.",
                        data_provenance="DERIVED",
                    )
                    team_findings.append(f_item)
                    unmet_requirements.append(
                        f"Member '{im.person_code}' movement state '{im.movement_state}' incompatible with field deployment"
                    )

            # Rule 3: Minimum Headcount Floor (Polar Buddy System)
            if team.mission_id and len(members) < 2:
                f_item = PersonnelSafetyFinding(
                    finding_id=f"FINDING-HEADCOUNT-{team.code}",
                    rule_id="TEAM_HEADCOUNT_DEFICIT",
                    status="BLOCKED",
                    subject_type="TEAM",
                    subject_id=team.id,
                    subject_code=team.code,
                    subject_name=team.name,
                    mission_id=mission.id if mission else None,
                    mission_code=mission.code if mission else None,
                    team_id=team.id,
                    team_code=team.code,
                    reason=(
                        f"Field team '{team.code}' has only {len(members)} assigned member(s), "
                        f"breaching mandatory polar 2-person buddy safety invariant."
                    ),
                    evidence={
                        "current_headcount": len(members),
                        "minimum_required": 2,
                    },
                    recommended_action="Assign additional personnel from station complement to satisfy safety floor.",
                    data_provenance="DERIVED",
                )
                team_findings.append(f_item)
                unmet_requirements.append(f"Team headcount ({len(members)}) below minimum safety floor (2)")

            # Rule 4: Team Leader Readiness
            if team.mission_id:
                if not leader:
                    f_item = PersonnelSafetyFinding(
                        finding_id=f"FINDING-LEADER-MISSING-{team.code}",
                        rule_id="TEAM_LEADER_UNREADY",
                        status="BLOCKED",
                        subject_type="TEAM",
                        subject_id=team.id,
                        subject_code=team.code,
                        subject_name=team.name,
                        mission_id=mission.id if mission else None,
                        mission_code=mission.code if mission else None,
                        team_id=team.id,
                        team_code=team.code,
                        reason=f"Field team '{team.code}' has no designated team leader.",
                        evidence={"leader_person_id": None},
                        recommended_action="Designate a certified team leader prior to mission dispatch.",
                        data_provenance="DERIVED",
                    )
                    team_findings.append(f_item)
                    unmet_requirements.append("Team lacks designated leader")
                elif leader.readiness_state != "READY":
                    f_item = PersonnelSafetyFinding(
                        finding_id=f"FINDING-LEADER-UNREADY-{leader.person_code}-{team.code}",
                        rule_id="TEAM_LEADER_UNREADY",
                        status="BLOCKED",
                        subject_type="PERSON",
                        subject_id=leader.id,
                        subject_code=leader.person_code,
                        subject_name=leader.full_name,
                        mission_id=mission.id if mission else None,
                        mission_code=mission.code if mission else None,
                        team_id=team.id,
                        team_code=team.code,
                        reason=(
                            f"Team leader '{leader.person_code}' ({leader.full_name}) is in state "
                            f"'{leader.readiness_state}', invalidating field operational leadership."
                        ),
                        evidence={
                            "leader_person_code": leader.person_code,
                            "leader_readiness": leader.readiness_state,
                        },
                        recommended_action="Reassign team leadership to a medically cleared senior specialist.",
                        data_provenance="DERIVED",
                    )
                    team_findings.append(f_item)
                    unmet_requirements.append(
                        f"Leader '{leader.person_code}' is in state '{leader.readiness_state}'"
                    )

            # Rule 5: Certified Field Safety Officer / Guide Presence
            # For field missions, warn if team lacks a dedicated safety guide or engineer
            if mission and (mission.type in ("FIELD_SURVEY", "TRAVERSE", "DRILLING") or team.status in ("FIELD", "DEPLOYED")):
                has_safety_role = any(
                    any(kw in m.role.lower() for kw in ("safety", "guide", "officer", "medic", "doctor"))
                    for m in members
                )
                if not has_safety_role:
                    f_item = PersonnelSafetyFinding(
                        finding_id=f"FINDING-SAFETY-ROLE-{team.code}",
                        rule_id="FIELD_SAFETY_OFFICER_ABSENT",
                        status="WARNING",
                        subject_type="TEAM",
                        subject_id=team.id,
                        subject_code=team.code,
                        subject_name=team.name,
                        mission_id=mission.id if mission else None,
                        mission_code=mission.code if mission else None,
                        team_id=team.id,
                        team_code=team.code,
                        reason=(
                            f"Field team '{team.code}' assigned to '{mission.code}' lacks an assigned "
                            f"certified Polar Field Safety Officer, guide, or medical officer."
                        ),
                        evidence={
                            "mission_type": mission.type,
                            "member_roles": [m.role for m in members],
                        },
                        recommended_action="Attach a certified Field Safety Officer or guide prior to departure.",
                        data_provenance="DERIVED",
                    )
                    team_findings.append(f_item)
                    unmet_requirements.append("Lacks certified Polar Field Safety Officer / Guide")

            # Determine team posture status
            if any(f.status == "BLOCKED" for f in team_findings):
                team_deployment_status = "BLOCKED"
            elif any(f.status == "WARNING" for f in team_findings):
                team_deployment_status = "WARNING"
            else:
                team_deployment_status = "CLEAR"

            posture = TeamDeploymentPosture(
                team_id=team.id,
                team_code=team.code,
                team_name=team.name,
                status=team.status,
                leader_person_id=leader.id if leader else None,
                leader_name=leader.full_name if leader else None,
                leader_readiness=leader.readiness_state if leader else None,
                mission_id=mission.id if mission else None,
                mission_code=mission.code if mission else None,
                location_id=loc.id if loc else None,
                location_name=loc.name if loc else None,
                headcount=len(members),
                members=[
                    {
                        "person_id": str(m.id),
                        "person_code": m.person_code,
                        "full_name": m.full_name,
                        "role": m.role,
                        "readiness_state": m.readiness_state,
                        "movement_state": m.movement_state,
                        "is_leader": leader.id == m.id if leader else False,
                    }
                    for m in members
                ],
                deployment_status=team_deployment_status,
                unmet_requirements=unmet_requirements,
                data_provenance="DERIVED",
            )
            team_postures.append(posture)
            findings.extend(team_findings)

        # 7. Roll up overall status deterministically
        if any(f.status == "BLOCKED" for f in findings):
            overall_status = "BLOCKED"
        elif any(f.status == "WARNING" for f in findings):
            overall_status = "WARNING"
        else:
            overall_status = "CLEAR"

        return PersonnelPostureSummary(
            expedition_id=expedition_id,
            overall_status=overall_status,
            total_personnel=total_personnel,
            cleared_count=cleared_count,
            medical_hold_count=medical_hold_count,
            unavailable_count=unavailable_count,
            at_station_count=at_station_count,
            field_deployed_count=field_deployed_count,
            in_transit_count=in_transit_count,
            teams=team_postures,
            findings=findings,
            reassignment_opportunities=reassignment_opportunities,
            evaluated_at=now,
            data_provenance="DERIVED",
        )
