// Creare's 'Implied Consent' EU Cookie Law Banner v:2.4
// Conceived by Robert Kent, James Bavington & Tom Foyster
// Put into a namespace and by Bjørn Rosell
//   Also changed behaviour so you have to click accept to make the banner stay away.
//   To make it behave like the original, set "createCookieWhenBannerIsShown" to true.

var CookieBanner = (function() {
    return {
        'createCookieWhenBannerIsShown': false,
        'createCookieWhenAcceptIsClicked': true,
        'cookieDuration': false,                   // Number of days before the cookie expires, and the banner reappears
        'cookieName': 'cookieConsent',          // Name of our cookie

        '_createDiv': function(html) {
            var bodytag = document.getElementsByTagName('body')[0];
            var div = document.createElement('div');
            div.setAttribute('id','cookie-law');
            div.innerHTML = html;

            // bodytag.appendChild(div); // Adds the Cookie Law Banner just before the closing </body> tag
            // or
            bodytag.insertBefore(div,bodytag.firstChild); // Adds the Cookie Law Banner just after the opening <body> tag

            document.getElementsByTagName('body')[0].className+=' cookiebanner'; //Adds a class tothe <body> tag when the banner is visible

            if (CookieBanner.createCookieWhenBannerIsShown) {
                CookieBanner.createAcceptCookie();
            }
        },

        '_createCookie': function(name, value, days) {
            var expires;
            if (days) {
                var date = new Date();
                date.setTime(date.getTime()+(days*24*60*60*1000));
                expires = "; expires="+date.toGMTString();
            }
            else {
                expires = "";
            }
            document.cookie = name+"="+value+expires+"; path=/";
        },

        '_checkCookie': function(name) {
            var nameEQ = name + "=";
            var ca = document.cookie.split(';');
            for(var i=0;i < ca.length;i++) {
                var c = ca[i];
                while (c.charAt(0)==' ') c = c.substring(1,c.length);
                if (c.indexOf(nameEQ) == 0) return c.substring(nameEQ.length,c.length);
            }
            return null;
        },

        '_eraseCookie': function(name) {
            CookieBanner._createCookie(name,"",-1);
        },

        'createCookie': function(cookieValue) {
            CookieBanner._createCookie(CookieBanner.cookieName, cookieValue, CookieBanner.cookieDuration); // Create the cookie
        },

        'closeBanner': function() {
            var element = document.getElementById('cookie-law');
            element.parentNode.removeChild(element);
        },

        'accept': function() {
            CookieBanner.createCookie('accepted');
            CookieBanner.closeBanner();
            var _paq = _paq || [];

            // Check if the title was set already somewhere else
            var documentTitleSet = false;
            for (var i = _paq.length - 1; i >= 0; i--) {
                if (_paq[i][0]=='setDocumentTitle'){
                    documentTitleSet = true;
                }
            }
            // only if it is not set set it here with the default
            if(!documentTitleSet){
                _paq.push(['setDocumentTitle', document.domain + '/' + document.title]);
            }

            _paq.push(['setDoNotTrack', true]);
            _paq.push(['trackPageView']);
            _paq.push(['enableLinkTracking']);
            (function() {
                var u='//nix.eox.at/piwik/';
                _paq.push(['setTrackerUrl', u+'piwik.php']);
                _paq.push(['setSiteId', 4]);
                var d=document, g=d.createElement('script'), s=d.getElementsByTagName('script')[0];
                g.type='text/javascript'; g.async=true; g.defer=true; g.src=u+'piwik.js'; s.parentNode.insertBefore(g,s);
            })();


        },

        'deny': function() {
            CookieBanner.createCookie('denied');
            CookieBanner.closeBanner();
        },

        'showUnlessInteracted': function(html) {
            if( (CookieBanner._checkCookie(CookieBanner.cookieName) != 'accepted') &&
                (CookieBanner._checkCookie(CookieBanner.cookieName) != 'denied') ){
                CookieBanner._createDiv(html);
            }
        }
    };
})();
