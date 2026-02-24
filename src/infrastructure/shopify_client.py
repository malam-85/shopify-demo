import httpx

from src.shared.decorators import log_errors


class ShopifyGraphQLError(Exception):
    """Raised when the Shopify API returns GraphQL errors."""


class ShopifyGraphQLClient:
    """Thin httpx wrapper for the Shopify Admin GraphQL API."""

    def __init__(self, shop_name: str, access_token: str, api_version: str) -> None:
        self._endpoint = (
            f"https://{shop_name}.myshopify.com/admin/api/{api_version}/graphql.json"
        )
        self._headers = {
            "X-Shopify-Access-Token": access_token,
            "Content-Type": "application/json",
        }

    @log_errors
    def execute(self, query: str, variables: dict | None = None) -> dict:
        """POST a GraphQL query and return the ``data`` payload.

        Raises:
            ShopifyGraphQLError: if the response contains a top-level ``errors`` key.
            httpx.HTTPStatusError: on non-2xx HTTP responses.
        """
        payload: dict = {"query": query}
        if variables:
            payload["variables"] = variables

        response = httpx.post(self._endpoint, headers=self._headers, json=payload)
        response.raise_for_status()

        body: dict = response.json()

        if errors := body.get("errors"):
            raise ShopifyGraphQLError(errors)

        return body
