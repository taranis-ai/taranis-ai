import requests
from flask import Blueprint, Flask, g, request
from flask.views import MethodView
from flask_jwt_extended import current_user
from models.collaboration import (
    CollabChannelCreate,
    CollabFinalizeRequest,
    CollabInviteRedeem,
    CollabLiveLockRequest,
    CollabLiveMoveNewsItem,
    CollabLivePresenceRequest,
    CollabLiveRemoveNewsItem,
    CollabLiveRemoveStory,
    CollabLiveReportPatch,
    CollabLiveSelectionClear,
    CollabLiveSelectionUpdate,
    CollabLiveStoryOpsSubmit,
    CollabLiveStoryPatch,
    CollabLiveWorkspacePatch,
    CollabMoveNewsItem,
    CollabPeerJoin,
    CollabPeerMoveNewsItem,
    CollabPeerStoriesAdd,
    CollabPeerStoryUpdate,
    CollabRemoteSync,
    CollabReportDraftCreate,
    CollabReportMembersReplace,
    CollabStoriesAdd,
    CollabStoryUpdate,
)
from pydantic import ValidationError

from core.config import Config
from core.managers.auth_manager import api_key_or_auth_required, auth_required
from core.model.user import User
from core.service.collaboration import collaboration_service


def _validation_error(exc: ValidationError) -> tuple[dict[str, str], int]:
    return {"error": str(exc)}, 400


def _story_payloads_from_ids(story_ids: list[str]) -> list[dict]:
    payloads: list[dict] = []
    for story_id in story_ids:
        payload, status = collaboration_service_story_access(story_id)
        if status == 200:
            payloads.append(payload)
    return payloads


def collaboration_service_story_access(story_id: str) -> tuple[dict, int]:
    from core.model.story import Story

    return Story.get_for_api(story_id, current_user)


def _local_actor_user(actor) -> User:
    if collaboration_service._normalize_base_url(actor.base_url) != collaboration_service.external_base_url():
        raise PermissionError("Report workspaces are local to this instance")
    user = User.get(actor.user_id) if actor.user_id is not None else User.find_by_name(actor.username)
    if not user or user.username != actor.username:
        raise PermissionError("Unknown local report workspace user")
    authenticated_user = getattr(g, "authenticated_user", None)
    if authenticated_user is not None and authenticated_user.id != user.id:
        raise PermissionError("Report workspace actor does not match the authenticated user")
    return user


def _peer_detail(detail) -> dict:
    return collaboration_service._peer_channel_payload(detail.model_dump(mode="json"))


class CollaborationChannels(MethodView):
    @auth_required("ASSESS_ACCESS")
    def get(self, channel_id: str | None = None):
        if channel_id:
            detail = collaboration_service.get_channel(channel_id, user=current_user)
            return detail.model_dump(mode="json", exclude_none=True), 200
        return collaboration_service.list_channels(current_user), 200

    @auth_required("ASSESS_UPDATE")
    def post(self):
        try:
            payload = CollabChannelCreate.model_validate(request.json or {})
        except ValidationError as exc:
            return _validation_error(exc)

        story_payloads = _story_payloads_from_ids(payload.story_ids)
        detail = collaboration_service.create_channel(payload.topic, story_payloads, current_user)
        return detail.model_dump(mode="json", exclude_none=True), 200


class CollaborationInviteRedeem(MethodView):
    @auth_required("ASSESS_UPDATE")
    def post(self):
        try:
            payload = CollabInviteRedeem.model_validate(request.json or {})
        except ValidationError as exc:
            return _validation_error(exc)

        try:
            detail = collaboration_service.redeem_invite(payload.owner_base_url, payload.channel_id, payload.token)
        except requests.RequestException as exc:
            return {"error": f"Failed to redeem collaboration invite: {exc}"}, 502
        return detail.model_dump(mode="json"), 200


class CollaborationStories(MethodView):
    @auth_required("ASSESS_UPDATE")
    def post(self, channel_id: str):
        try:
            payload = CollabStoriesAdd.model_validate(request.json or {})
        except ValidationError as exc:
            return _validation_error(exc)

        detail = collaboration_service.get_channel(channel_id, active_instance_base_url=collaboration_service.external_base_url())
        story_payloads = _story_payloads_from_ids(payload.story_ids)

        try:
            if detail.is_owner:
                updated = collaboration_service.add_story_payloads(channel_id, story_payloads, current_user)
            else:
                peer_payload = collaboration_service.get_channel(
                    channel_id, active_instance_base_url=collaboration_service.external_base_url()
                )
                response = requests.post(
                    f"{collaboration_service.api_root_url(detail.owner_base_url)}/assess/collab/channels/{channel_id}/peer-stories",
                    json={
                        "token": peer_payload.invite.token if peer_payload.invite else "",
                        "partner_base_url": collaboration_service.external_base_url(),
                        "stories": [
                            collaboration_service._build_snapshot_from_story(
                                story_payload, collaboration_service.external_base_url()
                            ).model_dump(mode="json")
                            for story_payload in story_payloads
                        ],
                    },
                    headers={"Content-type": "application/json"},
                    timeout=15,
                )
                response.raise_for_status()
                updated = collaboration_service.apply_remote_sync(
                    channel_id,
                    peer_payload.invite.token if peer_payload.invite else "",
                    response.json(),
                )
        except requests.RequestException as exc:
            return {"error": f"Failed to update collaboration channel: {exc}"}, 502

        return updated.model_dump(mode="json"), 200


class CollaborationPeerJoin(MethodView):
    def post(self, channel_id: str):
        try:
            payload = CollabPeerJoin.model_validate(request.json or {})
        except ValidationError as exc:
            return _validation_error(exc)

        try:
            detail = collaboration_service.join_owner_channel(channel_id, payload.token, payload.partner_base_url)
        except KeyError:
            return {"error": "Collaboration channel not found"}, 404
        except PermissionError as exc:
            return {"error": str(exc)}, 403
        except ValueError as exc:
            return {"error": str(exc)}, 400
        return _peer_detail(detail), 200


class CollaborationPeerStories(MethodView):
    def post(self, channel_id: str):
        try:
            payload = CollabPeerStoriesAdd.model_validate(request.json or {})
        except ValidationError as exc:
            return _validation_error(exc)

        try:
            detail = collaboration_service.add_peer_story_payloads(
                channel_id,
                payload.token,
                payload.partner_base_url,
                [story.model_dump(mode="json") for story in payload.stories],
            )
        except KeyError:
            return {"error": "Collaboration channel not found"}, 404
        except PermissionError as exc:
            return {"error": str(exc)}, 403
        except ValueError as exc:
            return {"error": str(exc)}, 400
        return _peer_detail(detail), 200


class CollaborationRemoteSync(MethodView):
    def post(self, channel_id: str):
        try:
            payload = CollabRemoteSync.model_validate(request.json or {})
        except ValidationError as exc:
            return _validation_error(exc)

        try:
            detail = collaboration_service.apply_remote_sync(channel_id, payload.token, payload.channel.model_dump(mode="json"))
        except PermissionError as exc:
            return {"error": str(exc)}, 403
        except ValueError as exc:
            return {"error": str(exc)}, 400
        return _peer_detail(detail), 200


class CollaborationLiveState(MethodView):
    @api_key_or_auth_required("ASSESS_ACCESS")
    def get(self, channel_id: str):
        authenticated_user = getattr(g, "authenticated_user", None)
        user_id = authenticated_user.id if authenticated_user is not None else request.args.get("user_id", type=int)
        detail = collaboration_service.get_channel(channel_id, user_id=user_id)
        return detail.model_dump(mode="json"), 200


class CollaborationLivePresenceConnect(MethodView):
    @api_key_or_auth_required()
    def post(self, channel_id: str):
        try:
            payload = CollabLivePresenceRequest.model_validate(request.get_json(silent=True) or {})
        except ValidationError as exc:
            return _validation_error(exc)

        detail = collaboration_service.register_presence(
            channel_id,
            participant_base_url=payload.actor.base_url,
            session_id=payload.actor.session_id,
            username=payload.actor.username,
            selected_story_id=payload.selected_story_id,
        )
        return detail.model_dump(mode="json"), 200


class CollaborationLivePresenceDisconnect(MethodView):
    @api_key_or_auth_required()
    def post(self, channel_id: str):
        try:
            payload = CollabLivePresenceRequest.model_validate(request.get_json(silent=True) or {})
        except ValidationError as exc:
            return _validation_error(exc)

        detail = collaboration_service.unregister_presence(
            channel_id,
            payload.actor.session_id,
            active_instance_base_url=payload.actor.base_url,
        )
        return detail.model_dump(mode="json"), 200


class CollaborationLiveLockAcquire(MethodView):
    @api_key_or_auth_required()
    def post(self, channel_id: str):
        try:
            payload = CollabLiveLockRequest.model_validate(request.get_json(silent=True) or {})
        except ValidationError as exc:
            return _validation_error(exc)

        try:
            if payload.draft_id and payload.field_key:
                detail = collaboration_service.acquire_report_lock(
                    channel_id,
                    payload.draft_id,
                    payload.field_key,
                    _local_actor_user(payload.actor),
                    payload.actor.session_id,
                    payload.actor.username,
                )
            elif payload.snapshot_id and payload.field_name:
                detail = collaboration_service.acquire_field_lock(
                    channel_id,
                    snapshot_id=payload.snapshot_id,
                    field_name=payload.field_name,
                    participant_base_url=payload.actor.base_url,
                    session_id=payload.actor.session_id,
                    username=payload.actor.username,
                    selected_story_id=payload.selected_story_id,
                )
            else:
                raise ValueError("A story or report field is required")
        except PermissionError as exc:
            return {"error": str(exc)}, 409
        except KeyError:
            return {"error": "Report draft not found"}, 404
        except ValueError as exc:
            return {"error": str(exc)}, 400
        return detail.model_dump(mode="json"), 200


class CollaborationLiveLockHeartbeat(MethodView):
    @api_key_or_auth_required()
    def post(self, channel_id: str):
        try:
            payload = CollabLiveLockRequest.model_validate(request.get_json(silent=True) or {})
        except ValidationError as exc:
            return _validation_error(exc)

        try:
            if payload.draft_id and payload.field_key:
                detail = collaboration_service.heartbeat_report_lock(
                    channel_id,
                    payload.draft_id,
                    payload.field_key,
                    _local_actor_user(payload.actor),
                    payload.actor.session_id,
                    payload.actor.username,
                )
            elif payload.snapshot_id and payload.field_name:
                detail = collaboration_service.heartbeat_field_lock(
                    channel_id,
                    snapshot_id=payload.snapshot_id,
                    field_name=payload.field_name,
                    participant_base_url=payload.actor.base_url,
                    session_id=payload.actor.session_id,
                    username=payload.actor.username,
                    selected_story_id=payload.selected_story_id,
                )
            else:
                raise ValueError("A story or report field is required")
        except PermissionError as exc:
            return {"error": str(exc)}, 409
        except KeyError:
            return {"error": "Report draft not found"}, 404
        except ValueError as exc:
            return {"error": str(exc)}, 400
        return detail.model_dump(mode="json"), 200


class CollaborationLiveLockRelease(MethodView):
    @api_key_or_auth_required()
    def post(self, channel_id: str):
        try:
            payload = CollabLiveLockRequest.model_validate(request.get_json(silent=True) or {})
        except ValidationError as exc:
            return _validation_error(exc)

        try:
            if payload.draft_id and payload.field_key:
                detail = collaboration_service.release_report_lock(
                    channel_id,
                    payload.draft_id,
                    payload.field_key,
                    _local_actor_user(payload.actor),
                    payload.actor.session_id,
                )
            elif payload.snapshot_id and payload.field_name:
                detail = collaboration_service.release_field_lock(
                    channel_id,
                    snapshot_id=payload.snapshot_id,
                    field_name=payload.field_name,
                    session_id=payload.actor.session_id,
                    active_instance_base_url=payload.actor.base_url,
                )
            else:
                raise ValueError("A story or report field is required")
        except PermissionError as exc:
            return {"error": str(exc)}, 409
        except ValueError as exc:
            return {"error": str(exc)}, 400
        return detail.model_dump(mode="json"), 200


class CollaborationLiveReportPatchView(MethodView):
    @api_key_or_auth_required()
    def post(self, channel_id: str):
        try:
            payload = CollabLiveReportPatch.model_validate(request.get_json(silent=True) or {})
            detail = collaboration_service.patch_report_draft(
                channel_id,
                payload.draft_id,
                payload.field_key,
                payload.value,
                _local_actor_user(payload.actor),
                payload.actor.session_id,
            )
        except ValidationError as exc:
            return _validation_error(exc)
        except KeyError:
            return {"error": "Report draft not found"}, 404
        except PermissionError as exc:
            return {"error": str(exc)}, 403
        except (TypeError, ValueError) as exc:
            return {"error": str(exc)}, 400
        return detail.model_dump(mode="json"), 200


class CollaborationLiveStoryPatchView(MethodView):
    @api_key_or_auth_required()
    def post(self, channel_id: str):
        try:
            payload = CollabLiveStoryPatch.model_validate(request.get_json(silent=True) or {})
        except ValidationError as exc:
            return _validation_error(exc)

        try:
            detail = collaboration_service.update_story_snapshot_live(
                channel_id,
                payload.snapshot_id,
                payload.payload.model_dump(exclude_none=True),
                participant_base_url=payload.actor.base_url,
                session_id=payload.actor.session_id,
                username=payload.actor.username,
                selected_story_id=payload.snapshot_id,
            )
        except PermissionError as exc:
            return {"error": str(exc)}, 409
        except KeyError:
            return {"error": "Collaboration story not found"}, 404
        except ValueError as exc:
            return {"error": str(exc)}, 400
        return detail.model_dump(mode="json"), 200


class CollaborationLiveStoryOpsView(MethodView):
    @api_key_or_auth_required()
    def post(self, channel_id: str):
        try:
            payload = CollabLiveStoryOpsSubmit.model_validate(request.get_json(silent=True) or {})
        except ValidationError as exc:
            return _validation_error(exc)

        try:
            detail, applied = collaboration_service.submit_story_ops_live(
                channel_id,
                snapshot_id=payload.snapshot_id,
                field_name=payload.field_name,
                version=payload.version,
                op_id=payload.op_id,
                updates=[item.model_dump(by_alias=True) for item in payload.updates],
                participant_base_url=payload.actor.base_url,
                session_id=payload.actor.session_id,
                username=payload.actor.username,
            )
        except KeyError:
            return {"error": "Collaboration story not found"}, 404
        except ValueError as exc:
            return {"error": str(exc)}, 400
        return {"channel": detail.model_dump(mode="json"), "applied": applied}, 200


class CollaborationLiveSelectionUpdateView(MethodView):
    @api_key_or_auth_required()
    def post(self, channel_id: str):
        try:
            payload = CollabLiveSelectionUpdate.model_validate(request.get_json(silent=True) or {})
        except ValidationError as exc:
            return _validation_error(exc)

        try:
            detail, selection = collaboration_service.update_story_selection_live(
                channel_id,
                snapshot_id=payload.snapshot_id,
                field_name=payload.field_name,
                anchor=payload.anchor,
                head=payload.head,
                participant_base_url=payload.actor.base_url,
                session_id=payload.actor.session_id,
                username=payload.actor.username,
            )
        except ValueError as exc:
            return {"error": str(exc)}, 400
        return {"channel": detail.model_dump(mode="json"), "selection": selection}, 200


class CollaborationLiveSelectionClearView(MethodView):
    @api_key_or_auth_required()
    def post(self, channel_id: str):
        try:
            payload = CollabLiveSelectionClear.model_validate(request.get_json(silent=True) or {})
        except ValidationError as exc:
            return _validation_error(exc)

        detail, cleared = collaboration_service.clear_story_selection_live(
            channel_id,
            snapshot_id=payload.snapshot_id,
            field_name=payload.field_name,
            participant_base_url=payload.actor.base_url,
            session_id=payload.actor.session_id,
        )
        return {"channel": detail.model_dump(mode="json"), "cleared": cleared}, 200


class CollaborationLiveMoveNewsItemView(MethodView):
    @api_key_or_auth_required()
    def post(self, channel_id: str):
        try:
            payload = CollabLiveMoveNewsItem.model_validate(request.get_json(silent=True) or {})
        except ValidationError as exc:
            return _validation_error(exc)

        try:
            detail = collaboration_service.move_news_item_live(
                channel_id,
                payload.source_snapshot_id,
                payload.target_snapshot_id,
                payload.news_item_id,
                participant_base_url=payload.actor.base_url,
                session_id=payload.actor.session_id,
                username=payload.actor.username,
            )
        except KeyError:
            return {"error": "Collaboration item not found"}, 404
        except PermissionError as exc:
            return {"error": str(exc)}, 409
        except ValueError as exc:
            return {"error": str(exc)}, 400
        return detail.model_dump(mode="json"), 200


class CollaborationLiveRemoveStoryView(MethodView):
    @api_key_or_auth_required()
    def post(self, channel_id: str):
        try:
            payload = CollabLiveRemoveStory.model_validate(request.get_json(silent=True) or {})
        except ValidationError as exc:
            return _validation_error(exc)

        try:
            detail = collaboration_service.remove_story_live(
                channel_id,
                payload.snapshot_id,
                participant_base_url=payload.actor.base_url,
                session_id=payload.actor.session_id,
                username=payload.actor.username,
            )
        except KeyError:
            return {"error": "Collaboration story not found"}, 404
        except PermissionError as exc:
            return {"error": str(exc)}, 409
        except ValueError as exc:
            return {"error": str(exc)}, 400
        return detail.model_dump(mode="json"), 200


class CollaborationLiveRemoveNewsItemView(MethodView):
    @api_key_or_auth_required()
    def post(self, channel_id: str):
        try:
            payload = CollabLiveRemoveNewsItem.model_validate(request.get_json(silent=True) or {})
        except ValidationError as exc:
            return _validation_error(exc)

        try:
            detail = collaboration_service.remove_news_item_live(
                channel_id,
                payload.snapshot_id,
                payload.news_item_id,
                participant_base_url=payload.actor.base_url,
                session_id=payload.actor.session_id,
                username=payload.actor.username,
            )
        except KeyError:
            return {"error": "Collaboration item not found"}, 404
        except PermissionError as exc:
            return {"error": str(exc)}, 409
        except ValueError as exc:
            return {"error": str(exc)}, 400
        return detail.model_dump(mode="json"), 200


class CollaborationLiveWorkspacePatchView(MethodView):
    @api_key_or_auth_required()
    def post(self, channel_id: str):
        try:
            payload = CollabLiveWorkspacePatch.model_validate(request.get_json(silent=True) or {})
        except ValidationError as exc:
            return _validation_error(exc)

        try:
            detail = collaboration_service.update_workspace_live(
                channel_id,
                {
                    "target": payload.target,
                    "action": payload.action,
                    "item_id": payload.item_id,
                    "data": payload.data,
                },
                participant_base_url=payload.actor.base_url,
                session_id=payload.actor.session_id,
                username=payload.actor.username,
                selected_story_id=payload.data.get("selected_story_id"),
            )
        except PermissionError as exc:
            return {"error": str(exc)}, 409
        except KeyError:
            return {"error": "Collaboration workspace item not found"}, 404
        except ValueError as exc:
            return {"error": str(exc)}, 400
        return detail.model_dump(mode="json"), 200


class CollaborationStoryUpdate(MethodView):
    @auth_required("ASSESS_UPDATE")
    def post(self, channel_id: str):
        try:
            payload = CollabStoryUpdate.model_validate(request.get_json(silent=True) or {})
        except ValidationError as exc:
            return _validation_error(exc)

        detail = collaboration_service.get_channel(channel_id, active_instance_base_url=collaboration_service.external_base_url())
        try:
            if detail.is_owner:
                updated = collaboration_service.update_story_snapshot(channel_id, payload.snapshot_id, payload.payload.model_dump())
            else:
                peer_payload = collaboration_service.get_channel(
                    channel_id, active_instance_base_url=collaboration_service.external_base_url()
                )
                response = requests.post(
                    f"{collaboration_service.api_root_url(detail.owner_base_url)}/assess/collab/channels/{channel_id}/peer-story-update",
                    json={
                        "token": peer_payload.invite.token if peer_payload.invite else "",
                        "partner_base_url": collaboration_service.external_base_url(),
                        "snapshot_id": payload.snapshot_id,
                        "payload": payload.payload.model_dump(),
                    },
                    headers={"Content-type": "application/json"},
                    timeout=15,
                )
                response.raise_for_status()
                updated = collaboration_service.apply_remote_sync(
                    channel_id,
                    peer_payload.invite.token if peer_payload.invite else "",
                    response.json(),
                )
        except requests.RequestException as exc:
            return {"error": f"Failed to update collaboration story: {exc}"}, 502
        except KeyError:
            return {"error": "Collaboration story not found"}, 404
        except ValueError as exc:
            return {"error": str(exc)}, 400

        return updated.model_dump(mode="json"), 200


class CollaborationPeerStoryUpdate(MethodView):
    def post(self, channel_id: str):
        try:
            payload = CollabPeerStoryUpdate.model_validate(request.get_json(silent=True) or {})
        except ValidationError as exc:
            return _validation_error(exc)

        try:
            detail = collaboration_service.update_peer_story_snapshot(
                channel_id, payload.token, payload.partner_base_url, payload.snapshot_id, payload.payload.model_dump()
            )
        except KeyError:
            return {"error": "Collaboration story not found"}, 404
        except PermissionError as exc:
            return {"error": str(exc)}, 403
        except ValueError as exc:
            return {"error": str(exc)}, 400
        return _peer_detail(detail), 200


class CollaborationMoveNewsItemView(MethodView):
    @auth_required("ASSESS_UPDATE")
    def post(self, channel_id: str):
        try:
            payload = CollabMoveNewsItem.model_validate(request.get_json(silent=True) or {})
        except ValidationError as exc:
            return _validation_error(exc)

        detail = collaboration_service.get_channel(channel_id, active_instance_base_url=collaboration_service.external_base_url())
        try:
            if detail.is_owner:
                updated = collaboration_service.move_news_item(
                    channel_id, payload.source_snapshot_id, payload.target_snapshot_id, payload.news_item_id
                )
            else:
                peer_payload = collaboration_service.get_channel(
                    channel_id, active_instance_base_url=collaboration_service.external_base_url()
                )
                response = requests.post(
                    f"{collaboration_service.api_root_url(detail.owner_base_url)}/assess/collab/channels/{channel_id}/peer-move-news-item",
                    json={
                        "token": peer_payload.invite.token if peer_payload.invite else "",
                        "partner_base_url": collaboration_service.external_base_url(),
                        "source_snapshot_id": payload.source_snapshot_id,
                        "target_snapshot_id": payload.target_snapshot_id,
                        "news_item_id": payload.news_item_id,
                    },
                    headers={"Content-type": "application/json"},
                    timeout=15,
                )
                response.raise_for_status()
                updated = collaboration_service.apply_remote_sync(
                    channel_id,
                    peer_payload.invite.token if peer_payload.invite else "",
                    response.json(),
                )
        except requests.RequestException as exc:
            return {"error": f"Failed to move collaboration news item: {exc}"}, 502
        except KeyError:
            return {"error": "Collaboration item not found"}, 404
        except ValueError as exc:
            return {"error": str(exc)}, 400
        return updated.model_dump(mode="json"), 200


class CollaborationPeerMoveNewsItemView(MethodView):
    def post(self, channel_id: str):
        try:
            payload = CollabPeerMoveNewsItem.model_validate(request.get_json(silent=True) or {})
        except ValidationError as exc:
            return _validation_error(exc)

        try:
            detail = collaboration_service.move_peer_news_item(
                channel_id,
                payload.token,
                payload.partner_base_url,
                payload.source_snapshot_id,
                payload.target_snapshot_id,
                payload.news_item_id,
            )
        except KeyError:
            return {"error": "Collaboration item not found"}, 404
        except PermissionError as exc:
            return {"error": str(exc)}, 403
        except ValueError as exc:
            return {"error": str(exc)}, 400
        return _peer_detail(detail), 200


class CollaborationReportCandidates(MethodView):
    @auth_required(["ASSESS_ACCESS", "ASSESS_UPDATE", "ANALYZE_ACCESS", "ANALYZE_CREATE", "ANALYZE_UPDATE"])
    def get(self, channel_id: str):
        try:
            return {"items": collaboration_service.report_member_candidates(channel_id, current_user)}, 200
        except KeyError:
            return {"error": "Collaboration channel not found"}, 404
        except PermissionError as exc:
            return {"error": str(exc)}, 403


class CollaborationReportTypes(MethodView):
    @auth_required(["ASSESS_ACCESS", "ASSESS_UPDATE", "ANALYZE_ACCESS", "ANALYZE_CREATE", "ANALYZE_UPDATE"])
    def get(self, channel_id: str):
        try:
            return {"items": collaboration_service.report_types(channel_id, current_user)}, 200
        except KeyError:
            return {"error": "Collaboration channel not found"}, 404
        except PermissionError as exc:
            return {"error": str(exc)}, 403


class CollaborationReportMembers(MethodView):
    @auth_required(["ASSESS_ACCESS", "ASSESS_UPDATE", "ANALYZE_ACCESS", "ANALYZE_CREATE", "ANALYZE_UPDATE"])
    def put(self, channel_id: str):
        try:
            payload = CollabReportMembersReplace.model_validate(request.get_json(silent=True) or {})
            detail = collaboration_service.replace_report_members(channel_id, payload.member_ids, current_user)
        except ValidationError as exc:
            return _validation_error(exc)
        except KeyError:
            return {"error": "Collaboration channel not found"}, 404
        except PermissionError as exc:
            return {"error": str(exc)}, 403
        except ValueError as exc:
            return {"error": str(exc)}, 400
        return detail.model_dump(mode="json"), 200


class CollaborationReportDrafts(MethodView):
    @auth_required(["ASSESS_ACCESS", "ASSESS_UPDATE", "ANALYZE_ACCESS", "ANALYZE_CREATE", "ANALYZE_UPDATE"])
    def post(self, channel_id: str):
        try:
            payload = CollabReportDraftCreate.model_validate(request.get_json(silent=True) or {})
            draft = collaboration_service.create_report_draft(channel_id, payload.report_item_type_id, current_user, payload.title)
        except ValidationError as exc:
            return _validation_error(exc)
        except KeyError:
            return {"error": "Collaboration channel not found"}, 404
        except PermissionError as exc:
            return {"error": str(exc)}, 403
        except ValueError as exc:
            return {"error": str(exc)}, 400
        return draft.model_dump(mode="json"), 201

    @auth_required(["ASSESS_ACCESS", "ASSESS_UPDATE", "ANALYZE_ACCESS", "ANALYZE_CREATE", "ANALYZE_UPDATE"])
    def delete(self, channel_id: str, draft_id: str):
        try:
            detail = collaboration_service.delete_report_draft(channel_id, draft_id, current_user)
        except KeyError:
            return {"error": "Report draft not found"}, 404
        except PermissionError as exc:
            return {"error": str(exc)}, 403
        except ValueError as exc:
            return {"error": str(exc)}, 400
        return detail.model_dump(mode="json"), 200


class CollaborationReportFinalize(MethodView):
    @auth_required(["ASSESS_ACCESS", "ASSESS_UPDATE", "ANALYZE_ACCESS", "ANALYZE_CREATE", "ANALYZE_UPDATE"])
    def post(self, channel_id: str, draft_id: str):
        try:
            report_id = collaboration_service.finalize_report_draft(channel_id, draft_id, current_user)
        except KeyError:
            return {"error": "Report draft not found"}, 404
        except PermissionError as exc:
            return {"error": str(exc)}, 403
        except ValueError as exc:
            return {"error": str(exc)}, 409
        except RuntimeError as exc:
            return {"error": str(exc)}, 500
        return {"report_id": report_id}, 200


class CollaborationFinalize(MethodView):
    @auth_required("ASSESS_UPDATE")
    def post(self, channel_id: str):
        try:
            payload = CollabFinalizeRequest.model_validate(request.get_json(silent=True) or {})
        except ValidationError as exc:
            return _validation_error(exc)

        try:
            result = collaboration_service.finalize_channel(channel_id, current_user, payload.story_ids or None)
        except ValueError as exc:
            return {"error": str(exc)}, 409
        return result.model_dump(mode="json"), 200


class CollaborationClose(MethodView):
    @auth_required("ASSESS_UPDATE")
    def post(self, channel_id: str):
        detail = collaboration_service.get_channel(channel_id, active_instance_base_url=collaboration_service.external_base_url())
        try:
            if detail.is_owner:
                closed = collaboration_service.close_channel(channel_id)
            else:
                response = requests.post(
                    f"{collaboration_service.api_root_url(detail.owner_base_url)}/assess/collab/channels/{channel_id}/close-owner",
                    json={"token": detail.invite.token if detail.invite else ""},
                    headers={"Content-type": "application/json"},
                    timeout=15,
                )
                response.raise_for_status()
                closed = collaboration_service.apply_remote_sync(
                    channel_id,
                    detail.invite.token if detail.invite else "",
                    response.json(),
                )
        except requests.RequestException as exc:
            return {"error": f"Failed to close collaboration channel: {exc}"}, 502
        return closed.model_dump(mode="json"), 200


class CollaborationOwnerClose(MethodView):
    def post(self, channel_id: str):
        token = (request.json or {}).get("token", "")
        try:
            channel = collaboration_service.get_channel(channel_id)
            if not channel.invite or channel.invite.token != token:
                return {"error": "Invalid collaboration token"}, 403
            closed = collaboration_service.close_channel(channel_id)
        except KeyError:
            return {"error": "Collaboration channel not found"}, 404
        return _peer_detail(closed), 200


def initialize(app: Flask):
    collab_bp = Blueprint("collaboration", __name__, url_prefix=f"{Config.APPLICATION_ROOT}api/assess/collab")

    collab_bp.add_url_rule("/channels", view_func=CollaborationChannels.as_view("collab_channels"), methods=["GET", "POST"])
    collab_bp.add_url_rule("/channels/<string:channel_id>", view_func=CollaborationChannels.as_view("collab_channel"), methods=["GET"])
    collab_bp.add_url_rule("/invites/redeem", view_func=CollaborationInviteRedeem.as_view("collab_redeem"), methods=["POST"])
    collab_bp.add_url_rule(
        "/channels/<string:channel_id>/stories", view_func=CollaborationStories.as_view("collab_stories"), methods=["POST"]
    )
    collab_bp.add_url_rule(
        "/channels/<string:channel_id>/story-update",
        view_func=CollaborationStoryUpdate.as_view("collab_story_update"),
        methods=["POST"],
    )
    collab_bp.add_url_rule("/channels/<string:channel_id>/join", view_func=CollaborationPeerJoin.as_view("collab_join"), methods=["POST"])
    collab_bp.add_url_rule(
        "/channels/<string:channel_id>/peer-story-update",
        view_func=CollaborationPeerStoryUpdate.as_view("collab_peer_story_update"),
        methods=["POST"],
    )
    collab_bp.add_url_rule(
        "/channels/<string:channel_id>/peer-stories",
        view_func=CollaborationPeerStories.as_view("collab_peer_stories"),
        methods=["POST"],
    )
    collab_bp.add_url_rule(
        "/channels/<string:channel_id>/move-news-item",
        view_func=CollaborationMoveNewsItemView.as_view("collab_move_news_item"),
        methods=["POST"],
    )
    collab_bp.add_url_rule(
        "/channels/<string:channel_id>/peer-move-news-item",
        view_func=CollaborationPeerMoveNewsItemView.as_view("collab_peer_move_news_item"),
        methods=["POST"],
    )
    collab_bp.add_url_rule(
        "/channels/<string:channel_id>/remote-sync",
        view_func=CollaborationRemoteSync.as_view("collab_remote_sync"),
        methods=["POST"],
    )
    collab_bp.add_url_rule(
        "/channels/<string:channel_id>/live-state",
        view_func=CollaborationLiveState.as_view("collab_live_state"),
        methods=["GET"],
    )
    collab_bp.add_url_rule(
        "/channels/<string:channel_id>/live/presence/connect",
        view_func=CollaborationLivePresenceConnect.as_view("collab_live_presence_connect"),
        methods=["POST"],
    )
    collab_bp.add_url_rule(
        "/channels/<string:channel_id>/live/presence/disconnect",
        view_func=CollaborationLivePresenceDisconnect.as_view("collab_live_presence_disconnect"),
        methods=["POST"],
    )
    collab_bp.add_url_rule(
        "/channels/<string:channel_id>/live/lock/acquire",
        view_func=CollaborationLiveLockAcquire.as_view("collab_live_lock_acquire"),
        methods=["POST"],
    )
    collab_bp.add_url_rule(
        "/channels/<string:channel_id>/live/lock/heartbeat",
        view_func=CollaborationLiveLockHeartbeat.as_view("collab_live_lock_heartbeat"),
        methods=["POST"],
    )
    collab_bp.add_url_rule(
        "/channels/<string:channel_id>/live/lock/release",
        view_func=CollaborationLiveLockRelease.as_view("collab_live_lock_release"),
        methods=["POST"],
    )
    collab_bp.add_url_rule(
        "/channels/<string:channel_id>/live/story-patch",
        view_func=CollaborationLiveStoryPatchView.as_view("collab_live_story_patch"),
        methods=["POST"],
    )
    collab_bp.add_url_rule(
        "/channels/<string:channel_id>/live/story-ops",
        view_func=CollaborationLiveStoryOpsView.as_view("collab_live_story_ops"),
        methods=["POST"],
    )
    collab_bp.add_url_rule(
        "/channels/<string:channel_id>/live/selection/update",
        view_func=CollaborationLiveSelectionUpdateView.as_view("collab_live_selection_update"),
        methods=["POST"],
    )
    collab_bp.add_url_rule(
        "/channels/<string:channel_id>/live/selection/clear",
        view_func=CollaborationLiveSelectionClearView.as_view("collab_live_selection_clear"),
        methods=["POST"],
    )
    collab_bp.add_url_rule(
        "/channels/<string:channel_id>/live/move-news-item",
        view_func=CollaborationLiveMoveNewsItemView.as_view("collab_live_move_news_item"),
        methods=["POST"],
    )
    collab_bp.add_url_rule(
        "/channels/<string:channel_id>/live/remove-story",
        view_func=CollaborationLiveRemoveStoryView.as_view("collab_live_remove_story"),
        methods=["POST"],
    )
    collab_bp.add_url_rule(
        "/channels/<string:channel_id>/live/remove-news-item",
        view_func=CollaborationLiveRemoveNewsItemView.as_view("collab_live_remove_news_item"),
        methods=["POST"],
    )
    collab_bp.add_url_rule(
        "/channels/<string:channel_id>/live/workspace-patch",
        view_func=CollaborationLiveWorkspacePatchView.as_view("collab_live_workspace_patch"),
        methods=["POST"],
    )
    collab_bp.add_url_rule(
        "/channels/<string:channel_id>/live/report-patch",
        view_func=CollaborationLiveReportPatchView.as_view("collab_live_report_patch"),
        methods=["POST"],
    )
    collab_bp.add_url_rule(
        "/channels/<string:channel_id>/report-candidates",
        view_func=CollaborationReportCandidates.as_view("collab_report_candidates"),
        methods=["GET"],
    )
    collab_bp.add_url_rule(
        "/channels/<string:channel_id>/report-types",
        view_func=CollaborationReportTypes.as_view("collab_report_types"),
        methods=["GET"],
    )
    collab_bp.add_url_rule(
        "/channels/<string:channel_id>/report-members",
        view_func=CollaborationReportMembers.as_view("collab_report_members"),
        methods=["PUT"],
    )
    collab_bp.add_url_rule(
        "/channels/<string:channel_id>/report-drafts",
        view_func=CollaborationReportDrafts.as_view("collab_report_drafts"),
        methods=["POST"],
    )
    collab_bp.add_url_rule(
        "/channels/<string:channel_id>/report-drafts/<string:draft_id>",
        view_func=CollaborationReportDrafts.as_view("collab_report_draft"),
        methods=["DELETE"],
    )
    collab_bp.add_url_rule(
        "/channels/<string:channel_id>/report-drafts/<string:draft_id>/finalize",
        view_func=CollaborationReportFinalize.as_view("collab_report_finalize"),
        methods=["POST"],
    )
    collab_bp.add_url_rule(
        "/channels/<string:channel_id>/finalize",
        view_func=CollaborationFinalize.as_view("collab_finalize"),
        methods=["POST"],
    )
    collab_bp.add_url_rule("/channels/<string:channel_id>/close", view_func=CollaborationClose.as_view("collab_close"), methods=["POST"])
    collab_bp.add_url_rule(
        "/channels/<string:channel_id>/close-owner",
        view_func=CollaborationOwnerClose.as_view("collab_close_owner"),
        methods=["POST"],
    )

    app.register_blueprint(collab_bp)
