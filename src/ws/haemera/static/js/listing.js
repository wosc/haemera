window.haemera = {};


haemera.ListingController = {
    data: {
        'actions': [],
        'current_row': null
    },

    update_url: null,
    _deleted: [],

    set: function(actions) {
        this.data.actions = actions;
    },

    create: function() {
        this.data.actions.push({'subject': 'New Action', 'status': 'todo'});
        this.data.current_row = this.data.actions.length - 1;
        Vue.nextTick(function() {
            document.querySelector('#subject').select();
        });
    },

    remove: function() {
        if (this.data.current_row == null || ! this.data.actions) return;
        if (this.data.actions[this.data.current_row].id) {
            this._deleted.push({
                'id': this.data.actions[this.data.current_row].id,
                'status': 'deleted'});
        }
        this.data.actions.splice(this.data.current_row, 1);
        this.data.current_row = null;
    },

    select_next: function() {
        if (this.data.current_row == null) {
            this.data.current_row = 0;
        } else if (this.data.current_row < this.data.actions.length - 1) {
            this.data.current_row++;
        }
    },

    select_previous: function() {
        if (this.data.current_row == null) {
            this.data.current_row = this.data.actions.length - 1;
        } else if (this.data.current_row > 0) {
            this.data.current_row--;
        }
    },

    select_none: function() {
        if (this.data.current_row != null) this.data.current_row = null;
    },

    select_row: function(row) {
        if (this.data.current_row == row) {
            this.data.current_row = null;
        } else {
            this.data.current_row = row;
        }
    },

    persist: function() {
        var self = this;
        window.fetch(self.update_url, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            // XXX Sending only dirty items would be more efficient, but how?
            body: JSON.stringify(self.data.actions.concat(self._deleted))
        }).then(function(response) {
            if (response.ok) {
                // XXX We may want to something more efficient here, like
                // replacing self.data.actions with a server-side result.
                window.location.reload();
            } else {
                window.alert(self.update_url + ' returned ' + response.status);
            }
        }).catch(function(error) {
            throw error;
        });
    }
};
var Controller = haemera.ListingController;


var ListingView = new Vue({
    el: '#listing',
    template: '#template-listing',
    data: {
        'context': Controller.data
    },
    methods: {
        select_row: function(event) {
            var tr = closest(event.target, 'tr');
            var position = Array.prototype.indexOf.call(
                tr.parentNode.querySelectorAll('tr'), tr);
            Controller.select_row(position);
        }
    }
});


var DetailView = new Vue({
    el: '#detail',
    template: '#template-detail',
    data: {
        'context': Controller.data
    },
    computed: {
        'action': function() {
            return this.context.actions[this.context.current_row];
        }
    }
});


var closest = function(el, tag) {
    tag = tag.toUpperCase();
    do {
        if (el.tagName == tag) return el;
        el = el.parentNode;
    } while (el)
};


document.querySelector('body').addEventListener('keyup', function(event) {
    if (event.target.tagName == 'INPUT' ||
        event.target.tagName == 'SELECT' ||
        event.target.tagName == 'TEXTAREA') {
        return;
    }

    if (event.key == 'm') {
        Controller.create();
    } else if (event.key == 'Delete' || event.key == 'd') {
        Controller.remove();
    } else if (event.key == 'j') {
        Controller.select_next();
    } else if (event.key == 'k') {
        Controller.select_previous();
    } else if (event.key == 'i') {
        Controller.select_none();
    } else if (event.key == '$') {
        Controller.persist();
    }
});
