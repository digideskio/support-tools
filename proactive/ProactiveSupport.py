# TODO use from string import Template?
# would mean variables specified with $

jira_user_dict = {}
jira_user_dict["jacob.ribnik"] = {'name': "Jake",
                                  'signoff': "Jake"}
jira_user_dict["ruairi.newman"] = {'name': "Ruairi",
                                   'signoff': "Regards,\n\nRuairi"}

jira_users = jira_user_dict.keys()


# quick and dirty for now
def get(jira_user, param):
    return jira_user_dict[jira_user][param]


def renderDescription(text, config):
    for param in config:
        text = text.replace("<<" + param + ">>", config[param])
    return text
