# -----------------------------
# Base Image (JDK 21)
# -----------------------------
FROM eclipse-temurin:21-jdk-jammy

# -----------------------------
# Install Kotlin Compiler
# -----------------------------
RUN apt-get update && \
    apt-get install -y unzip curl && \
    rm -rf /var/lib/apt/lists/*

# Install Kotlin (stable version)
ENV KOTLIN_VERSION=1.9.24
RUN curl -L -o kotlin.zip \
    https://github.com/JetBrains/kotlin/releases/download/v${KOTLIN_VERSION}/kotlin-compiler-${KOTLIN_VERSION}.zip && \
    unzip kotlin.zip -d /opt && \
    rm kotlin.zip

# Add Kotlin to PATH
ENV PATH="/opt/kotlinc/bin:${PATH}"

# -----------------------------
# Create Non-Root User
# -----------------------------
RUN useradd -m -u 1001 judgeuser

# -----------------------------
# Install Jackson Libraries
# -----------------------------
RUN mkdir -p /opt/libs
WORKDIR /opt/libs

RUN curl -L -o jackson-core.jar \
    https://repo1.maven.org/maven2/com/fasterxml/jackson/core/jackson-core/2.17.0/jackson-core-2.17.0.jar && \
    curl -L -o jackson-databind.jar \
    https://repo1.maven.org/maven2/com/fasterxml/jackson/core/jackson-databind/2.17.0/jackson-databind-2.17.0.jar && \
    curl -L -o jackson-annotations.jar \
    https://repo1.maven.org/maven2/com/fasterxml/jackson/core/jackson-annotations/2.17.0/jackson-annotations-2.17.0.jar

# -----------------------------
# Working Directory
# -----------------------------
WORKDIR /app

# -----------------------------
# Drop Privileges
# -----------------------------
#USER judgeuser

# -----------------------------
# Default Command
# -----------------------------
CMD ["sleep", "300"]
