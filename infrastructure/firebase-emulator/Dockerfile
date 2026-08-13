FROM node:24.18.0-bookworm-slim

ENV FIREBASE_TOOLS_DISABLE_UPDATE_CHECK=true \
    XDG_CONFIG_HOME=/tmp/firebase

RUN npm install --global firebase-tools@15.24.0

WORKDIR /workspace
COPY --chown=node:node firebase.json .firebaserc ./

USER node
EXPOSE 9099

CMD ["firebase", "emulators:start", "--only", "auth", "--project", "tmi-local"]
