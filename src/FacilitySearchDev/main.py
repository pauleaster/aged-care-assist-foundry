# Copyright (c) Microsoft. All rights reserved.

import os

from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient
from agent_framework_foundry_hosting import ResponsesHostServer
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def main():
    client = FoundryChatClient(
        project_endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
        model=os.environ["AZURE_AI_MODEL_DEPLOYMENT_NAME"],
        credential=DefaultAzureCredential(),
    )

    mcp_tool = client.get_mcp_tool(
        name="aged-care-mcp",
        url=os.environ["AGED_CARE_MCP_URL"],
        approval_mode="never_require",
        allowed_tools=[
            "search_facilities",
            "get_facility_details",
            "get_rooms_for_facility",
        ],
    )

    agent = Agent(
        client=client,
        instructions=(
            "You are FacilitySearchDev, an assistant for exploring aged-care "
            "facility information. You have access to an MCP data source with tools "
            "for searching aged-care facilities and retrieving facility and room "
            "details. For questions about facility availability, pricing, ratings, "
            "room details, or facility details, use the available MCP tools rather "
            "than relying on general knowledge. "
            "You must not invent facility names, contact details, vacancies, prices, "
            "room types, ratings, or availability. Answer only from retrieved tool "
            "data and clearly state any limitations. "
            "The search_facilities tool returns data as a list of JSON-like facility "
            "objects. Each object represents one facility. When the returned list "
            "contains multiple objects, treat each object as a separate matching "
            "facility and list every returned facility unless the user explicitly "
            "asks for fewer results. Do not answer using only the first object in "
            "the list. Do not claim there are no other matching facilities unless "
            "the returned list is empty or contains no other matching objects. "
            "For each listed facility, include facility_name, facility_address_full, "
            "overall_star_rating if available, and room_count or matching_room_count "
            "if available. If the user asks to exclude a facility, remove only that "
            "facility from the returned list and continue listing the remaining "
            "returned facilities."
        ),
        tools=[mcp_tool],
        # History will be managed by the hosting infrastructure, thus there
        # is no need to store history by the service. Learn more at:
        # https://developers.openai.com/api/reference/resources/responses/methods/create
        default_options={"store": False},
    )

    server = ResponsesHostServer(agent)
    server.run()


if __name__ == "__main__":
    main()
