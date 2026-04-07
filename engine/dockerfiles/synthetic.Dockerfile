FROM computer-use-gui:local

# Copy synthetic data collection files
COPY --chown=computeruse:computeruse engine/gui/synthetic_data_collection/synthetic_script.py /home/computeruse/
COPY --chown=computeruse:computeruse engine/gui/synthetic_data_collection/synthetic_mouse_path.py /home/computeruse/
COPY --chown=computeruse:computeruse engine/gui/synthetic_data_collection/record_script.py /home/computeruse/
COPY --chown=computeruse:computeruse engine/gui/synthetic_data_collection/requirements.txt /home/computeruse/

# Install additional requirements for synthetic data collection
USER root
RUN pip3 install -r /home/computeruse/requirements.txt
USER computeruse

# Set Python path
ENV PYTHONPATH=/home/computeruse

# Create raw_data directory
RUN mkdir -p /home/computeruse/raw_data

WORKDIR /home/computeruse
