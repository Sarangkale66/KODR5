import { Strategy as GoogleStrategy } from "passport-google-oauth20"

const googleConfig = {
   clientID: process.env.GOOGLE_CLIENT_ID,
   clientSecret: process.env.GOOGLE_CLIENT_SECRET,
   callbackURL: process.env.GOOGLE_CALLBACK_URL
};

export const getGoogleStrategy = () => {
    return new GoogleStrategy(
        googleConfig,
        (at, rt, profile, cb) => { // ye google kaa hai!!!
            const user = {
                provider: 'google',
                id: profile.id,
                name: profile.displayName || 'Google User',
                email: profile.emails && profile.emails.length > 0 ? profile.emails[0].value : 'No email',
                avatar: profile.photos && profile.photos.length > 0 ? profile.photos[0].value : 'https://via.placeholder.com/150'
            };

            return cb(null, user)
        }
    )
}