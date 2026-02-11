#!/usr/bin/env bats

setup() {
    export TEST_HOME="/tmp/ccc-test-$$"
    mkdir -p "$TEST_HOME"
    export CONTINUUM_REPO_URL=""
}

teardown() {
    rm -rf "$TEST_HOME"
}

@test "ccc fails when CONTINUUM_REPO_URL set but no deploy key" {
    export CONTINUUM_REPO_URL="git@github.com:test/repo.git"
    export HOME="$TEST_HOME"

    run ./ccc --version

    [ "$status" -eq 1 ]
    [[ "$output" =~ "deploy key not found" ]]
}

@test "ccc runs without CONTINUUM_REPO_URL (local mode)" {
    export HOME="$TEST_HOME"

    # Mock docker to just echo
    function docker() { echo "docker called: $@"; }
    export -f docker

    run ./ccc --help

    [ "$status" -eq 0 ]
}
