# LLMDFA: Analyzing Dataflow in Code with Large Language Models

LLMDFA is a LLM-powered data-flow analysis framework. Specifically, it instantiates bottom-up summary-based data-flow analysis by interpreting intra-procedural data-flow facts with LLMs. With the specified sources/sinks and data-flow transfer function (i.e., rules of propagating data-flow facts), LLMDFA can support various forms of bug detection in a context- and path-sensitive manner. Notably, the analysis is totally compilation-free.

## Installation

1. Clone the repository:
    ```shell
    git clone git@github.com:chengpeng-wang/LLMDFA.git
    cd LLMDFA
    ```

2. Install the required dependencies:
    ```shell
    conda create --name llmdfa python=3.10
    conda activate llmdfa
    pip install -r requirements.txt
    ```

3. Ensure you have the Tree-sitter library and language bindings installed:
    ```shell
    cd lib
    python build.py
    ```

4. Configure the keys:
    ```shell
    export OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    ```

## Quick Start

1. Analyze a demo case using LLMDFA

    First, you need to synthesize the source/sink extractor with the following command:

    ```shell
    cd src
    sh run_extractor_synthesizer.sh
    ```

    After that, you can obtain synthesized extractors in the file `src/TSAgent/TS_synthesis_extractor.py`. We also provide the manually crafted extractors in `src/TSAgent/TS_manual_extractor.py`. If you want to use the manually crafted ones, you can just overwrite `src/TSAgent/TS_synthesis_extractor.py` with the content of `src/TSAgent/TS_manual_extractor.py`.

    Then we can run the following commands to detect the XSS bugs using LLMDFA powered by gpt-4o-mini as a demo, which contain 10 cases.

    ```shell
    cd src
    python run_llmdfa.py --bug-type xss --model-name gpt-4o-mini \
        -syn-parser -fscot -syn-solve \
        --solving-refine-number 3 \
        --analysis-mode single    
    ```

    Then you can obtain the bug report in the directory `log/gpt-4o-mini/synparser_fscot_synsolver`. Also, the console output indicate the numbers of TPs and FPs. Here is an example:

    ```
    CWE369_Divide_by_Zero__int_database_modulo_81 

    {'input_token_cost': 14237, 'output_token_cost': 973, 'analysis_result': {'TPs': 1, 'FPs': 0}, 'ground_truth': {'TPs': 1, 'FPs': 2}, 'single time cost': 16.143609285354614} 
    ```

    In the above example, the case `CWE369_Divide_by_Zero__int_database_modulo_81` contains 1 true positive and 2 cases that are easily reported as false positives. The above console output indicates that LLMDFA report one true postive without false positive. The input and output costs are 14237 and 973, respectively. The time cost is 16.143609285354614 seconds.

    If you want to detect all the XSS bugs in the Juliet Test Suite, you can just change the value of `analysis-mode` to `all`.

    If you want to change the bug types, you can reset the value of `bug-type` to `osci` and `dbz`.

    If you want to change the LLMs, you can just change the value of `model-name` to the name of the models you want to use, such as `gpt-3.5-turbo` and `gpt-4-turbo`. The output reports of LLMDFA are stored in the separate directory in `log` when using different LLMs.


2. Run ablations of LLMDFA

   You can run the three ablations of LLMDFA as follows:

   - NoSynExt: Utilize LLMs to identify sources and sinks instead of applying synthesized source/sink extractors

    ```shell
    cd src
    python run_llmdfa.py --bug-type xss --model-name gpt-4o-mini \
        -fscot -syn-solve \
        --solving-refine-number 3 \
        --analysis-mode single    
    ```

   - NoCoT: Directly ask LLMs to summarize intra-procedural data-flow paths without chain-of-thought prompting

    ```shell
    cd src
    python run_llmdfa.py --bug-type xss --model-name gpt-4o-mini \
        -syn-parser -syn-solve \
        --solving-refine-number 3 \
        --analysis-mode single    
    ```

   - NoSynVal: Validate path feasibility with LLMs instead of invoking SMT solvers

    ```shell
    cd src
    python run_llmdfa.py --bug-type xss --model-name gpt-4o-mini \
        -syn-parser -fscot \
        --solving-refine-number 3 \
        --analysis-mode single    
    ```

   The bug reports of the ablations are located in `log/gpt-4o-mini/nosynparser_fscot_synsolver`, `log/gpt-4o-mini/synparser_nofscot_synsolver`, and `log/gpt-4o-mini/synparser_fscot_nosynsolver`, respectively.

3. Run end-to-end prompting-based analyses as baselines

   You can run the following command to apply end-to-end prompting-based analyzers:

    ```shell
    cd src
    python run_baseline.py --bug-type xss --model-name gpt-4o-mini --analysis-mode single    
    ```
   
## Remark on Dataset

To avoid the leakage of ground truth to LLMs, we obfuscate the code in the Juliet Test Suite. Specifically, we remove the comments and rename the functions. Also, we concatenate multiple Java files belonging to the same test case into a single file for convenience in prompting, even though the resulting file may not be compilable.

## More Programming Languages

LLMDFA is language-agnostic. To migrate the current implementations to other programming languages or extract more syntactic facts, please refer to the grammar files in the corresponding Tree-sitter libraries and refactor the code in the directory `src/TSAgent`. Basically, you only need to change the node types when invoking `find_nodes`.

Here are the links to grammar files in Tree-sitter libraries targeting mainstream programming languages:

- C: https://github.com/tree-sitter/tree-sitter-c/blob/master/src/grammar.json
- C++: https://github.com/tree-sitter/tree-sitter-cpp/blob/master/src/grammar.json
- Java: https://github.com/tree-sitter/tree-sitter-java/blob/master/src/grammar.json
- Python: https://github.com/tree-sitter/tree-sitter-python/blob/master/src/grammar.json
- JavaScript: https://github.com/tree-sitter/tree-sitter-javascript/blob/master/src/grammar.json

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any improvements or bug fixes.

## Contact

For any questions or suggestions, please contact [wang6590@purdue.edu](mailto:wang6590@purdue.edu) or [stephenw.wangcp@gmail.com](mailto:stephenw.wangcp@gmail.com).