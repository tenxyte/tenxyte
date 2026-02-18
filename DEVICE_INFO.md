Voici des exemples concrets pour chaque plateforme :

### Desktop

```
# Windows 10 — Chrome
v=1|os=windows;osv=10|device=desktop|arch=x64|runtime=chrome;rtv=122

# Windows 11 — Firefox
v=1|os=windows;osv=11|device=desktop|arch=x64|runtime=firefox;rtv=133

# Windows 11 — Edge
v=1|os=windows;osv=11|device=desktop|arch=x64|runtime=edge;rtv=121

# macOS — Safari
v=1|os=macos;osv=14.3|device=desktop|arch=arm64|runtime=safari;rtv=17.3

# macOS — Chrome
v=1|os=macos;osv=15.0|device=desktop|arch=arm64|runtime=chrome;rtv=122

# Linux — Firefox
v=1|os=linux|device=desktop|arch=x64|runtime=firefox;rtv=133
```

### Mobile

```
# iPhone — Safari (iOS 17)
v=1|os=ios;osv=17.3|device=mobile|arch=arm64|runtime=safari;rtv=17.3

# iPhone — Chrome
v=1|os=ios;osv=17.3|device=mobile|arch=arm64|runtime=chrome;rtv=122

# Android — Chrome (Samsung Galaxy)
v=1|os=android;osv=14|device=mobile|arch=arm64|runtime=chrome;rtv=122

# Android — Firefox
v=1|os=android;osv=13|device=mobile|arch=arm64|runtime=firefox;rtv=133
```

### Tablettes

```
# iPad — Safari
v=1|os=ios;osv=17.3|device=tablet|arch=arm64|runtime=safari;rtv=17.3

# Android Tablet — Chrome
v=1|os=android;osv=14|device=tablet|arch=arm64|runtime=chrome;rtv=122
```

### Avec app + timezone (format complet)

```
# App mobile Android
v=1|os=android;osv=14|device=mobile|arch=arm64|app=monapp;appv=2.1.0|runtime=react-native;rtv=0.73|tz=Africa/Porto-Novo

# App desktop Windows (Electron)
v=1|os=windows;osv=11|device=desktop|arch=x64|app=monapp;appv=1.4.2|runtime=electron;rtv=28|tz=Europe/Paris
```

### Minimal (strictement valide)

```
# Minimum requis : juste la version
v=1|device=desktop

# OS + device seulement
v=1|os=windows|device=mobile
```

Les champs `app`, `arch`, `tz` sont optionnels. Seul `v=1` est obligatoire pour passer la validation.