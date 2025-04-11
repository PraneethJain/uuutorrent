import httpx
from typing import Optional
from fastapi import HTTPException, status

from app.schemas.anilist import AnilistEntry, AnilistMedia

ANILIST_URL = "https://graphql.anilist.co"


class AnilistService:

    async def _make_request(
        self, user_token: str, query: str, variables: Optional[dict] = None
    ) -> dict:
        headers = {
            "Authorization": f"Bearer {user_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        json_payload = {"query": query}
        if variables:
            json_payload["variables"] = variables

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    ANILIST_URL, json=json_payload, headers=headers, timeout=20.0
                )
                response.raise_for_status()
                data = response.json()
                if "errors" in data:
                    print(f"Anilist API Error: {data['errors']}")
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"Anilist API error: {data['errors'][0]['message']}",
                    )
                return data["data"]
            except httpx.RequestError as exc:
                print(f"An error occurred while requesting {exc.request.url!r}.")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Could not connect to Anilist API.",
                )
            except httpx.HTTPStatusError as exc:
                print(
                    f"HTTP error {exc.response.status_code} while requesting {exc.request.url!r}."
                )
                if exc.response.status_code == 401:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid Anilist token.",
                    )
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Anilist API returned status {exc.response.status_code}",
                )

    async def get_viewer_id(self, user_token: str) -> int:
        query = """
        query {
            Viewer { id }
        }
        """
        data = await self._make_request(user_token, query)
        if not data or "Viewer" not in data or "id" not in data["Viewer"]:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not retrieve Viewer ID from Anilist.",
            )
        return data["Viewer"]["id"]

    async def get_user_list(self, user_token: str, user_id: int) -> list[AnilistEntry]:
        """
        Fetches the user's 'CURRENT' watching list from Anilist.
        """
        query = """
        query ($userId: Int, $status: MediaListStatus) {
            MediaListCollection (userId: $userId, status: $status, type: ANIME) {
                lists {
                    name
                    entries {
                        media {
                            id
                            title { romaji english native userPreferred }
                            format status description episodes duration source
                            mediaListEntry { progress }
                            nextAiringEpisode { airingAt timeUntilAiring episode }
                        }
                    }
                }
            }
        }
        """
        variables = {"userId": user_id, "status": "CURRENT"}
        data = await self._make_request(user_token, query, variables)

        if (
            not data
            or "MediaListCollection" not in data
            or not data["MediaListCollection"].get("lists")
        ):
            print(f"Unexpected Anilist response structure for user list: {data}")
            return []

        entries_data = data["MediaListCollection"]["lists"][0].get("entries", [])

        try:
            watchlist = [AnilistEntry(**entry) for entry in entries_data]
            return watchlist
        except Exception as e:
            print(f"Error parsing Anilist watchlist data: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to parse watchlist data from Anilist.",
            )

    async def set_progress(self, user_token: str, media_id: int, progress: int) -> bool:
        """
        Sets the progress for a given media ID on Anilist. Returns True on success.
        """
        query = """
        mutation ($mediaId: Int, $progress: Int) {
            SaveMediaListEntry(mediaId: $mediaId, progress: $progress) {
                id # Request some field to confirm success
            }
        }
        """
        variables = {"mediaId": media_id, "progress": progress}
        try:
            data = await self._make_request(user_token, query, variables)
            return (
                "SaveMediaListEntry" in data and data["SaveMediaListEntry"] is not None
            )
        except HTTPException as e:
            raise e
        except Exception as e:
            print(f"Unexpected error setting Anilist progress: {e}")
            return False

    async def get_media_details(
        self, user_token: str, media_id: int
    ) -> Optional[AnilistMedia]:
        """
        Fetches details for a specific media item from Anilist using its ID.
        Returns an AnilistMedia object or None if not found.
        """
        query = """
        query ($id: Int) {
            Media (id: $id, type: ANIME) {
                id
                title { romaji english native userPreferred }
                format status description episodes duration source
                # Add any other fields you might eventually need
            }
        }
        """
        variables = {"id": media_id}
        try:
            data = await self._make_request(user_token, query, variables)

            if not data or "Media" not in data or data["Media"] is None:
                print(f"No media details found on Anilist for ID: {media_id}")
                return None
            media_data = data["Media"]
            return AnilistMedia(**media_data)

        except HTTPException as e:
            if e.status_code == 404:
                print(f"Anilist returned 404 for media ID: {media_id}")
                return None
            raise e
        except Exception as e:
            print(
                f"Unexpected error fetching Anilist media details for {media_id}: {e}"
            )
            return None


anilist_service = AnilistService()
