FROM node:20-slim

WORKDIR /app

# Copy package.json and package-lock.json first for caching
COPY package.json package-lock.json ./

# Install dependencies
RUN npm install

# Copy the rest of the application code
COPY . .

# Change ownership of the /app directory to the non-root 'node' user
# The 'node' user and group already exist in the node:20-slim image.
RUN chown -R node:node /app

# Switch to the non-root 'node' user
USER node

# Set environment variables
ENV PORT=5006

# Expose the port
EXPOSE 5006

# Command to run the application
CMD ["npm", "start"]