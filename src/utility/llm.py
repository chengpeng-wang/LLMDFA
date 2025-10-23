from openai import *
import sys
import tiktoken
from typing import Tuple
import time
import signal
from pathlib import Path
import replicate
import google.generativeai as genai


class LLM:
    """
    An online inference model using ChatGPT
    """

    def __init__(
        self,
        online_model_name: str,
        openai_key: str,
        temperature: float,
        system_role="",
    ) -> None:
        """
        Initialize the LLM with model name, OpenAI key, and temperature.
        :param online_model_name: Name of the online model to use
        :param openai_key: API key for OpenAI
        :param temperature: Temperature setting for the model
        """
        self.online_model_name = online_model_name
        self.encoding = tiktoken.encoding_for_model("gpt-3.5-turbo-0125")
        self.openai_key = openai_key
        self.temperature = temperature
        self.systemRole = system_role

    # Main Inference Function
    def infer(self, message: str, is_measure_cost: bool = True) -> Tuple[str, int, int]:
        """
        Perform inference using the specified online model.
        :param message: The input message for the model
        :param is_measure_cost: Flag to measure token cost
        :return: Tuple containing the output, input token cost, and output token cost
        """
        output = ""

        if "gemini" in self.online_model_name:
            output = self.infer_with_gemini(message)
        elif "claude" in self.online_model_name:
            output = self.infer_claude(message)
        elif "gpt" in self.online_model_name:
            output = self.infer_with_openai_model(message)

        input_token_cost = (
            0
            if not is_measure_cost
            else len(self.encoding.encode(self.systemRole))
            + len(self.encoding.encode(message))
        )
        output_token_cost = (
            0 if not is_measure_cost else len(self.encoding.encode(output))
        )
        return output, input_token_cost, output_token_cost

    # Inference with Gemini
    def infer_with_gemini(self, message: str) -> str:
        """
        Perform inference using the Gemini model.
        :param message: The input message for the model
        :return: The output from the model
        """

        def timeout_handler(signum, frame):
            raise TimeoutError("ChatCompletion timeout")

        def simulate_ctrl_c(signal, frame):
            raise KeyboardInterrupt("Simulating Ctrl+C")

        gemini_model = genai.GenerativeModel("gemini-pro")
        signal.signal(signal.SIGALRM, timeout_handler)

        received = False
        tryCnt = 0
        while not received:
            tryCnt += 1
            try:
                signal.alarm(50)  # Set a timeout of 50 seconds
                message = self.systemRole + "\n" + message

                safety_settings = [
                    {"category": "HARM_CATEGORY_DANGEROUS", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {
                        "category": "HARM_CATEGORY_HATE_SPEECH",
                        "threshold": "BLOCK_NONE",
                    },
                    {
                        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                        "threshold": "BLOCK_NONE",
                    },
                    {
                        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                        "threshold": "BLOCK_NONE",
                    },
                ]

                response = gemini_model.generate_content(
                    message,
                    safety_settings=safety_settings,
                    generation_config=genai.types.GenerationConfig(
                        temperature=self.temperature
                    ),
                )
                signal.alarm(0)  # Cancel the timeout
                output = response.text
                return output
            except TimeoutError:
                received = False
                simulate_ctrl_c(None, None)  # Simulate Ctrl+C effect
            except KeyboardInterrupt:
                received = False
                continue
            except Exception:
                return ""
            if tryCnt > 5:
                return ""

    # Inference with Claude
    def infer_claude(self, message: str) -> str:
        """
        Perform inference using the Claude model.
        :param message: The input message for the model
        :return: The output from the model
        """

        def timeout_handler(signum, frame):
            raise TimeoutError("ChatCompletion timeout")

        def simulate_ctrl_c(signal, frame):
            raise KeyboardInterrupt("Simulating Ctrl+C")

        input = [
            {"role": "system", "content": self.systemRole},
            {"role": "user", "content": message},
        ]
        signal.signal(signal.SIGALRM, timeout_handler)

        received = False
        tryCnt = 0
        while not received:
            tryCnt += 1
            try:
                signal.alarm(60)  # Set a timeout of 60 seconds
                openai.api_key = self.openai_key
                response = openai.ChatCompletion.create(
                    model=self.online_model_name,
                    messages=input,
                    temperature=self.temperature,
                )
                signal.alarm(0)  # Cancel the timeout
                output = response.choices[0].message.content
                return output
            except TimeoutError:
                received = False
                simulate_ctrl_c(None, None)  # Simulate Ctrl+C effect
            except KeyboardInterrupt:
                return ""
            except Exception:
                received = False
            if tryCnt > 5:
                return ""

    # Inference with OpenAI Model
    def infer_with_openai_model(self, message: str) -> str:
        """
        Perform inference using the OpenAI model.
        :param message: The input message for the model
        :return: The output from the model
        """

        def timeout_handler(signum, frame):
            raise TimeoutError("ChatCompletion timeout")

        def simulate_ctrl_c(signal, frame):
            raise KeyboardInterrupt("Simulating Ctrl+C")

        model_input = [
            {"role": "system", "content": self.systemRole},
            {"role": "user", "content": message},
        ]

        received = False
        tryCnt = 0
        output = ""

        signal.signal(signal.SIGALRM, timeout_handler)
        while not received:
            tryCnt += 1
            try:
                signal.alarm(10)  # Set a timeout of 10 seconds
                client = OpenAI(api_key=self.openai_key)
                response = client.chat.completions.create(
                    model=self.online_model_name,
                    messages=model_input,
                    temperature=self.temperature,
                )
                signal.alarm(0)  # Cancel the timeout
                output = response.choices[0].message.content
                received = True
                break
            except TimeoutError:
                received = False
                simulate_ctrl_c(None, None)  # Simulate Ctrl+C effect
            except KeyboardInterrupt:
                output = ""
                break
            except Exception:
                received = False
            if tryCnt > 5:
                output = ""
        return output
