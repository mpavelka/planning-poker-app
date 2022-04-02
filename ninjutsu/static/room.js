
function runRoomApp(room_uuid, selector) {
  const audioVolume = 0.2;
  function newAudio(url, volume) {
      const audio = new Audio(url);
      audio.volume = volume ? volume : audioVolume;
      return audio;
  }
  const ninjaScreamAudio = [
      // newAudio('/static/audio/202037__thestigmata__man-die.mp3'),
      newAudio('/static/audio/369593__eflexmusic__hard-punch-to-gut-indoor-large-room.mp3', audioVolume+0.2),
      newAudio('/static/audio/44267__erdie__male-fight07.mp3', audioVolume+0.2),
      newAudio('/static/audio/442288__rockittt__male-pain-sound-effects-A.mp3', audioVolume+0.2),
      newAudio('/static/audio/442288__rockittt__male-pain-sound-effects-B.mp3', audioVolume+0.2),
      newAudio('/static/audio/442288__rockittt__male-pain-sound-effects-C.mp3', audioVolume+0.2),
  ]
  const swordSliceAudio = [
      newAudio('/static/audio/344131__thebuilder15__sword-slice.mp3'),
      newAudio('/static/audio/591155__ultraaxvii__sword-contact-with-swipe.mp3'),
      newAudio('/static/audio/462983__bastianhallo__knife-being-sharpened.mp3'),
      newAudio('/static/audio/504615__neospica__slicing-through-flesh.mp3'),
  ]


  return Vue.createApp({
  	beforeCreate: function() {
      this.playerId = null;
      this.playerVote = null;
      this.sound = true;
	  },
    data() {
      const data = {
        msg: "msg",
        playerId: this.playerId,
        playerVote: this.playerVote,
        status: this.status,
        votes: this.votes,
        sound: this.sound,
      }
      return data;
    },

    mounted() {
      const that = this;
      // The websocket
      this.socket = new WebSocket((window.location.protocol == "https:" ? "wss://" : "ws://")+window.location.host+window.location.pathname+'/ws')
      // Connection opened
      this.socket.addEventListener('open', function (event) {
        if (window.location.search.includes("observer")) {
          that.socket.send("GETSTATE")
        } else {
        	that.socket.send("JOIN")
        }
      });
      // Listen for messages
      this.socket.addEventListener('message', function (event) {
          // Parse event
          const parts = event.data.split(" ");
          const evName = parts[0]

          switch(evName) {
              case "WELCOME":
                  that.playerId = parts[1];
                  break;

              case "VOTE":
                  // Sword slice!
                  if (that.sound) {
                      const sound = swordSliceAudio[Math.floor(Math.random() * swordSliceAudio.length)];
                      sound.pause();
                      sound.currentTime = 0;
                      sound.play()
                      break;
                  }

              case "ROOM_STATE":
                  const status = parts[1]

                  switch(status) {
                      case "PROGRESS":
                          that.status = status
                          that.votes = parts.slice(2).map(user => {
                              const parts = user.split(":")
                              return {
                                  playerId: parseInt(parts[0]),
                                  value: parts[1].toLowerCase() == "true",
                              }
                          })
                          break;

                      case "RESULT":
                          if (that.sound && that.status != "RESULT") {
                              // Hai!
                              const sound = ninjaScreamAudio[Math.floor(Math.random() * ninjaScreamAudio.length)];
                              sound.pause();
                              sound.currentTime = 0;
                              sound.play()
                          }
                          that.status = status
                          that.playerVote = null;
                          that.votes = parts.slice(2).map(user => {
                              const parts = user.split(":")
                              return {
                                  playerId: parseInt(parts[0]),
                                  value: parseInt(parts[1]),
                              }
                          })
                          break;
                  }
                  break;
          }
          console.log('Message from server ', event.data);
      });
    },

    unmounted() {
      this.socket.close()
    },

    methods: {
      vote(value) {
        this.playerVote = value;
        this.socket.send("VOTE "+value);
      },
      reset(value) {
        this.socket.send("RESET")
      },
      getVoteDisplayValue(vote) {
          if (this.status == "RESULT") {
              return vote.value;
          }
          if (vote.playerId == this.playerId) {
              return this.playerVote ? this.playerVote : "?"
          }
          return vote.value ? "X" : "-";
      },
      toggleSound() {
          this.sound = !this.sound;
      }
    }

  }).mount(selector)
}