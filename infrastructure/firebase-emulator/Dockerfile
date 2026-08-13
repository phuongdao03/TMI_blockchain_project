FROM node:24.18.0-alpine3.24

ENV FIREBASE_TOOLS_DISABLE_UPDATE_CHECK=true \
    XDG_CONFIG_HOME=/tmp/firebase

RUN npm install --global firebase-tools@15.26.0 \
    && rm -rf /usr/local/lib/node_modules/npm

WORKDIR /workspace
COPY --chown=node:node firebase.json .firebaserc ./

USER node
EXPOSE 9099

CMD ["firebase", "emulators:start", "--only", "auth", "--project", "tmi-local"]
