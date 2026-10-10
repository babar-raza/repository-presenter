cargo --version
cargo test --all-targets > out.txt 2>&1; echo "cargo test --all-targets exit: $?"
grep -E '^(running [0-9]+ tests?|test result:)' out.txt | sort | uniq -c
