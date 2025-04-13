FROM continuumio/miniconda3:25.1.1-2


WORKDIR /webapp

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    gh \
    htop \
    less \
    mc \
    nano \
    tmux \
    tree \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Copy environment file first for better caching
COPY conda_env.yml .

# Create conda environment
RUN conda env create -f conda_env.yml

# Make RUN commands use the new environment
SHELL ["conda", "run", "-n", "app_env", "/bin/bash", "-c"]

# Copy application code
COPY . .

RUN mkdir -p $HOME/.config/mc
RUN cp ./container_additions/mc_ini $HOME/.config/mc/ini
RUN cp ./container_additions/.tmux.conf $HOME

RUN echo "alias ls='ls --color=auto'" >> ~/.bashrc && \
    echo "alias ll='ls --color=auto -l'" >> ~/.bashrc && \
    echo "alias l='ls --color=auto -lA'" >> ~/.bashrc && \
    echo "conda activate app_env" >> ~/.bashrc

RUN echo "source ~/.bashrc"

# Expose ports (FastAPI and Streamlit)
EXPOSE 8000 8501

# The command will be overwritten by docker-compose
CMD ["bash"]
