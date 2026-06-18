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

    agent = Agent(
        client=client,
        instructions=(
            "You are FacilitySearchDev, an assistant for exploring aged-care "
            "facility information. You must not invent facility names, contact "
            "details, vacancies, prices, room types, ratings, or availability. "
            "You currently do not have access to live aged-care facility data "
            "unless a tool, uploaded file, or knowledge source is connected. "
            "If the user asks for facility availability, pricing, ratings, or "
            "room details and no data source is available, say that you need a "
            "connected data source before answering. When a data source is "
            "connected, answer only from retrieved data and clearly state any "
            "limitations."
        ),
        # History will be managed by the hosting infrastructure, thus there
        # is no need to store history by the service. Learn more at:
        # https://developers.openai.com/api/reference/resources/responses/methods/create
        default_options={"store": False},
    )

    server = ResponsesHostServer(agent)
    server.run()


if __name__ == "__main__":
    main()
