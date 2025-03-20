#!/bin/bash
read -sp "Enter your OpenAI API Key: " api_key
echo
export OPENAI_API_KEY="$api_key"
echo "export OPENAI_API_KEY=\"$api_key\"" >> ~/.bashrc  # Use ~/.zshrc for Zsh users
echo "Exported API Key, please run 'source ~/.bashrc' to apply the changes (or source ~/.zshrc for Zsh users)."