#! /usr/bin/env bash

MODEL=gpt-4o-mini

python3 TSAgent/synthesis/main.py --extractor dbz_src --model "$MODEL" --output-file _dbz_src_extractor.py
python3 TSAgent/synthesis/main.py --extractor dbz_sink --model "$MODEL" --output-file _dbz_sink_extractor.py
python3 TSAgent/synthesis/main.py --extractor xss_src --model "$MODEL" --output-file _xss_src_extractor.py
python3 TSAgent/synthesis/main.py --extractor xss_sink --model "$MODEL" --output-file _xss_sink_extractor.py
python3 TSAgent/synthesis/main.py --extractor ci_src --model "$MODEL" --output-file _ci_src_extractor.py
python3 TSAgent/synthesis/main.py --extractor ci_sink --model "$MODEL" --output-file _ci_sink_extractor.py

# merge
cat _dbz_src_extractor.py _dbz_sink_extractor.py _xss_src_extractor.py _xss_sink_extractor.py _ci_src_extractor.py _ci_sink_extractor.py > _extractors.py

# replace
rm TSAgent/TS_synthesis_extractor.py 
cp _extractors.py TSAgent/TS_synthesis_extractor.py

# delete all the files starting from "_"
rm _*.py
