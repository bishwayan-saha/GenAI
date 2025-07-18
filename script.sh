#!/bin/bash

# Define colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print a message in green
print_success() {
    echo -e "${GREEN}$1${NC}"
}

# Function to print a message in red
print_error() {
    echo -e "${RED}$1${NC}"
}

# Function to print a message in yellow
print_info() {
    echo -e "${YELLOW}$1${NC}"
}

# Read input from JSON file
echo "Please paste the JSON content (single or multi-line) and press Ctrl+D when done:"
JSON_CONTENT=$(cat)

username=$(echo "$JSON_CONTENT" | grep -oP '"username"\s*:\s*"\K[^"]+')
loginServer=$(echo "$JSON_CONTENT" | grep -oP '"loginServer"\s*:\s*"\K[^"]+')
refreshToken=$(echo "$JSON_CONTENT" | grep -oP '"refreshToken"\s*:\s*"\K[^"]+')

if [[ -z "$username" || -z "$loginServer" || -z "$refreshToken" ]]; then
    print_error "Invalid JSON input. Ensure it contains 'username', 'loginServer', and 'refreshToken'."
    exit 1
fi

# Validate inputs (redundant check, but kept from original script)
if [[ -z "$username" || -z "$loginServer" || -z "$refreshToken" ]]; then
    print_error "All fields (username, loginServer, refreshToken) are required in the JSON file."
    exit 1
fi

# Update LOGIN_SERVER in .env file
ENV_FILE="./.env"
if sudo grep -q "^LOGIN_SERVER=" "$ENV_FILE"; then
    sudo sed -i "s|^LOGIN_SERVER=.*|LOGIN_SERVER=$loginServer|" "$ENV_FILE"
else
    echo "LOGIN_SERVER=$loginServer" | sudo tee -a "$ENV_FILE" > /dev/null
fi

# Ask user if they want to clean up Docker containers and images
read -p "$(print_info 'Do you want to clean up Docker containers and images before proceeding? (Y/n): ')" cleanup_choice
cleanup_choice=${cleanup_choice:-Y} # Default to 'Y' if no input

if [[ "$cleanup_choice" =~ ^[Yy]$ ]]; then
    # Stop and remove containers with names containing "interopae"
    print_info "Stopping Docker containers with names containing 'interopae'..."
    containers_to_remove=$(sudo docker container ls -aq --filter "name=interopae")
    if [[ -n "$containers_to_remove" ]]; then
        sudo docker container stop $containers_to_remove
        print_success "Stopped containers: $containers_to_remove"
        sudo docker container rm $containers_to_remove
        print_success "Removed containers: $containers_to_remove"
    else
        print_info "No containers found with names containing 'interopae'."
    fi

    # Remove images with names containing "interopae"
    print_info "Removing Docker images with names containing 'interopae'..."
    images_to_remove=$(sudo docker image ls --format "{{.Repository}}:{{.Tag}}" | grep -E "interopae") # Added mongo-express to image removal as it's common in such setups
    if [[ -n "$images_to_remove" ]]; then
        sudo docker image rm $images_to_remove
        print_success "Removed images: $images_to_remove"
    else
        print_info "No images found with names containing 'interopae'."
    fi

    # Prune unused Docker objects
    print_info "Pruning unused Docker objects..."
    sudo docker system prune -af
    print_success "Docker system pruned."
else
    print_info "Skipping Docker container and image cleanup as per your choice."
fi

# --- MongoDB Export Section ---
    echo ""
    read -p "$(print_info 'Do you want to export (dump) the MongoDB data? (Y/n): ')" dump_choice
    dump_choice=${dump_choice:-Y}

    if [[ "$dump_choice" =~ ^[Yy]$ ]]; then
        # Ensure mongod is running
        print_info "Starting MongoDB service (mongod)..."
        sudo systemctl start mongod

        read -p "$(print_info 'Please provide the MongoDB connection string: ')" mongo_conn
        if [[ -z "$mongo_conn" ]]; then
            print_error "No connection string provided. Skipping MongoDB export."
        else
            print_info "Exporting MongoDB data to interopdb_data..."
            mongodump --uri="$mongo_conn" --archive=interopdb_data
            if [[ $? -eq 0 ]]; then
                print_success "MongoDB data exported successfully to interopdb_data."
                sudo systemctl stop mongod
            else
                print_error "Failed to export MongoDB data."
            fi
        fi
    else
        print_info "Skipping MongoDB data export as per your choice."
    fi

# Log in to the Docker registry
print_info "Logging in to Docker registry..."
sudo docker login "$loginServer" -u "$username" -p "$refreshToken"

if [[ $? -eq 0 ]]; then
    print_success "Successfully logged in to Docker registry."

    # --- Image Selection Logic ---
    print_info "Fetching available images from $loginServer..."
    # Attempt to list images from the registry. This might require specific API calls
    # or a 'docker search' equivalent that works with private registries.
    # For simplicity, we'll provide a dummy list for demonstration.
    # In a real-world scenario, you'd likely use 'skopeo list-tags' or a registry API.

    # Dummy list of images for demonstration purposes.
    # Replace this with actual logic to fetch images from your private registry.
    # Example: images=$(curl -s -H "Authorization: Bearer <your_token>" "https://$loginServer/v2/_catalog" | jq -r '.repositories[]')
    declare -a available_images=(
        "interopae/interopae_agent"
        "interopae/interopae_auth"
        "interopae/interopae_ui"
        # Add more images relevant to your docker-compose setup
    )

    if [ ${#available_images[@]} -eq 0 ]; then
        print_error "No images found in the registry or unable to fetch image list."
        exit 1
    fi

    echo ""
    print_info "Please choose which images to pull by entering their corresponding numbers (e.g., 1 3 for Service A and Service C):"
    for i in "${!available_images[@]}"; do
        echo "$((i+1)). ${available_images[i]}"
    done

    read -p "$(print_info 'Enter your choices: ')" chosen_indices

    selected_images=()
    for index in $chosen_indices; do
        if [[ "$index" -gt 0 && "$index" -le "${#available_images[@]}" ]]; then
            selected_images+=("${available_images[$((index-1))]}")
        else
            print_error "Invalid selection: $index. Skipping."
        fi
    done

    if [ ${#selected_images[@]} -eq 0 ]; then
        print_error "No valid images selected. Exiting."
        exit 1
    fi

    echo ""
    print_info "Pulling selected images..."
    for image in "${selected_images[@]}"; do
        print_info "Pulling $loginServer/$image..."
        sudo docker pull "$loginServer/$image"
        if [[ $? -eq 0 ]]; then
            print_success "Successfully pulled $image."
        else
            print_error "Failed to pull $image."
        fi
    done

    # --- End Image Selection Logic ---

    # Use docker-compose to build and run the services
    print_info "Starting services using docker-compose..."
    export LOGIN_SERVER="$loginServer"
    cd "$(dirname "$0")"  # Change to the directory containing the docker-compose.yaml
    sudo docker-compose -f docker-compose.yaml up -d --remove-orphans

    if [[ $? -eq 0 ]]; then
        print_success "Services started successfully using docker-compose."
    else
        print_error "Failed to start services using docker-compose."
    fi

else
    print_error "Failed to log in to Docker registry. Please check your credentials."
fi
