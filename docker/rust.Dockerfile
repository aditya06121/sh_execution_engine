FROM rust:1.75-slim

WORKDIR /opt/cache

# Create dummy project
RUN cargo new runner

WORKDIR /opt/cache/runner

# Add dependencies (no duplicate header)
RUN echo 'serde = { version = "1", features = ["derive"] }' >> Cargo.toml \
 && echo 'serde_json = "1"' >> Cargo.toml

# Vendor dependencies
RUN cargo vendor vendor

# Configure Cargo to use vendored sources
RUN mkdir -p .cargo && \
    printf '[source.crates-io]\nreplace-with = "vendored-sources"\n\n[source.vendored-sources]\ndirectory = "vendor"\n' > .cargo/config.toml

# Prebuild dependencies
RUN cargo build --release

WORKDIR /app

CMD ["sleep", "300"]