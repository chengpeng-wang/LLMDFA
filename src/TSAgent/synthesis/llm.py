from abc import ABC, abstractmethod
import os
import tiktoken
from logging import Logger
from pathlib import Path
from typing import Literal

import openai
import google.generativeai as genai
import anthropic
import signal

keys = os.environ.get("OPENAI_API_KEY").split(":")


class LLM(ABC):
    def __init__(self, api_key: str, temperature: float = 0, log_file: Path = None):
        self.log_file = log_file
        self.api_key = api_key
        self.temperature = temperature
        self.conversation = []
        self.index = 0

    def reset_cost(self):
        self.input_token_cost = 0
        self.output_token_cost = 0

    def set_system_role(self, role: str):
        self.conversation = [{"role": "system", "content": role}] + self.conversation

    @staticmethod
    def build_message(prompt: str, role: Literal["user", "assistant"] = "user") -> dict:
        return {
            "role": role,
            "content": prompt,
        }

    def __copy__(self):
        """
        Fork the conversation.
        """
        gpt = GPT(self.api_key, self.model, self.temperature, self.log_file)
        gpt.conversation = self.conversation.copy()
        gpt.index = self.index
        return gpt

    def log(self, message: str):
        if self.log_file:
            with open(self.log_file, "a") as f:
                f.write(message + "\n")

    def query(self, prompt: str, with_history=False) -> str:
        self.index += 1
        self.conversation.append(self.build_message(prompt, role="user"))
        self.log(f"*****************Prompt Start {self.index}*****************")
        self.log(prompt)
        self.log(f"*****************Prompt End {self.index}*******************")
        text = self._query_model(with_history)
        self.log(f"*****************Response Start {self.index}*****************")
        self.log(text)
        self.log(f"*****************Response End {self.index}*******************")
        self.conversation.append(self.build_message(text, role="assistant"))
        return text

    @abstractmethod
    def _query_model(self, with_history=False) -> str:
        pass


class GPT(LLM):
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-3.5-turbo-1106",
        temperature: float = 0,
        log_file: Path = None,
    ):
        super().__init__(api_key, temperature, log_file)
        self.model = model
        self.client = openai.OpenAI(
            api_key=self.api_key,
        )
        self.encoder = tiktoken.encoding_for_model(self.model)
        self.input_token_cost = 0
        self.output_token_cost = 0

    def _query_model(self, with_history=False) -> str:
        input_messages = self.conversation if with_history else [self.conversation[-1]]
        for m in input_messages:
            self.input_token_cost += len(self.encoder.encode(m["content"]))
        response = self.client.chat.completions.create(
            model=self.model,
            messages=input_messages,
            temperature=self.temperature,
        )
        text = response.choices[0].message.content
        output_tokens = self.encoder.encode(text)
        self.output_token_cost += len(output_tokens)
        return text


class Gemini(LLM):
    def __init__(
        self,
        api_key: str,
        model: str = "gemini-pro",
        temperature: float = 0,
        log_file: Path = None,
    ):
        super().__init__(api_key, temperature, log_file)
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)
        self.input_token_cost = 0
        self.output_token_cost = 0

    def _query_model(self, with_history=False) -> str:
        message = (
            "\n".join([m["content"] for m in self.conversation])
            if with_history
            else self.conversation[-1]["content"]
        )
        response = self.model.generate_content(
            message, generation_config={"temperature": self.temperature}
        )
        output = response.text
        return output


class Claude(LLM):
    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-haiku-20240307",
        temperature: float = 0,
        log_file: Path = None,
    ):
        super().__init__(api_key, temperature, log_file)
        self.model_name = model
        self.model = anthropic.Anthropic(api_key=api_key)
        self.temperature = temperature
        self.input_token_cost = 0
        self.output_token_cost = 0

    def infer_with_gpt_or_claude(self, message: str = ""):
        def timeout_handler(signum, frame):
            raise TimeoutError("ChatCompletion timeout")

        def simulate_ctrl_c(signal, frame):
            raise KeyboardInterrupt("Simulating Ctrl+C")

        input = [
            {"role": "system", "content": "you are a good programmer"},
            {"role": "user", "content": message},
        ]
        signal.signal(signal.SIGALRM, timeout_handler)

        received = False
        tryCnt = 0
        while not received:
            tryCnt += 1
            try:
                signal.alarm(20)  # Set a timeout of 20 seconds
                # openai.api_key = self.openai_key
                openai.api_key = keys[0]
                response = openai.ChatCompletion.create(
                    model="claude-3-opus-20240229", messages=input, temperature=0.0
                )

                signal.alarm(0)  # Cancel the timeout
                output = response.choices[0].message.content
                print("Inference succeeded...")
                return output
            except TimeoutError:
                print("ChatCompletion call timed out")
                received = False
                simulate_ctrl_c(None, None)  # Simulate Ctrl+C effect
            except KeyboardInterrupt:
                print("ChatCompletion cancelled by user")
                return ""
            except Exception:
                received = False
            if tryCnt > 5:
                return ""

    def _query_model(self, with_history=False) -> str:
        input_messages = self.conversation if with_history else [self.conversation[-1]]
        print(input_messages)
        output = self.infer_with_gpt_or_claude(str(input_messages))
        print(output)
        return output

        # response = self.model.messages.create(
        #     max_tokens=4096,
        #     model=self.model_name,
        #     messages=input_messages,
        #     temperature=self.temperature,
        # )
        # text = response.content[0]
        # return text.text
