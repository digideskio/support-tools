package com.mongodb.support.emea;

import com.atlassian.jira.rest.client.api.JiraRestClient;
import com.atlassian.jira.rest.client.api.JiraRestClientFactory;
import com.atlassian.jira.rest.client.api.domain.BasicIssue;
import com.atlassian.jira.rest.client.api.domain.Comment;
import com.atlassian.jira.rest.client.api.domain.Issue;
import com.atlassian.jira.rest.client.api.domain.SearchResult;
import com.atlassian.jira.rest.client.internal.async.AsynchronousJiraRestClientFactory;
import org.joda.time.DateTime;

import java.io.*;
import java.net.URI;
import java.util.*;
import java.util.concurrent.ExecutionException;
import java.util.stream.StreamSupport;

/**
 * Created by ricardolorenzo on 20/07/15.
 */
public class JiraIssues {
    private static final Long HOURS_PER_DAY = (24 * 60 * 60 * 1000L);
    private static String USER = "support-emea-tc@10gen.com";
    private static String PASSWORD = "Powerbook17";
    private static List<String> teamMembers;
    private static String ftsLabel = "fs";
    private static Integer order;

    /**
     * Stats rows
     */
    private static Map<String, Integer> issuesFTS;
    private static Map<String, Integer> issuesP1;
    private static Map<String, Integer> issuesP2;
    private static Map<String, Integer> issuesOther;

    /**
     * Days without an update per type
     */
    private static Map<String, Integer> issuesFTSDaysWithoutUpdate;
    private static Map<String, Integer> issuesP1DaysWithoutUpdate;
    private static Map<String, Integer> issuesP2DaysWithoutUpdate;
    private static Map<String, Integer> issuesOtherDaysWithoutUpdate;

    /**
     * Days without an update per type
     */
    private static Map<String, Integer> longWaitingActiveTickets;

    static {
        issuesFTS = new HashMap<String, Integer>();
        issuesP1 = new HashMap<String, Integer>();
        issuesP2 = new HashMap<String, Integer>();
        issuesOther = new HashMap<String, Integer>();
        issuesFTSDaysWithoutUpdate = new HashMap<String, Integer>();
        issuesP1DaysWithoutUpdate = new HashMap<String, Integer>();
        issuesP2DaysWithoutUpdate = new HashMap<String, Integer>();
        issuesOtherDaysWithoutUpdate = new HashMap<String, Integer>();
        teamMembers = new ArrayList<String>();
        longWaitingActiveTickets = new HashMap<>();
    }

    private static synchronized void increaseMemberValue(Map<String, Integer> map, String member, Integer value) {
        Integer newValue = map.getOrDefault(member, 0) + value;
        map.put(member, newValue);
    }

    private static void checkFTSLabel(Issue issue, Integer days, Boolean FTS) {
        increaseMemberValue(issuesFTS, issue.getAssignee().getName(), 1);
        increaseMemberValue(issuesFTSDaysWithoutUpdate, issue.getAssignee().getName(), days);
        FTS = true;
    }

    private static void readMembers(final File membersFile) throws IOException {
        BufferedReader buffer = new BufferedReader(new FileReader(membersFile));
        try {
            String line;
            while((line = buffer.readLine()) != null) {
                if(line.startsWith("#")) {
                    continue;
                }
                teamMembers.add(line);
            }
        } finally {
            buffer.close();
        }
    }

    private static void processIssue(JiraRestClient jc, BasicIssue basicIssue) throws ExecutionException,
            InterruptedException {
        Boolean FTS = false;
        Issue issue = jc.getIssueClient().getIssue(basicIssue.getKey()).claim();

        DateTime lastDate = issue.getCreationDate();
        for(Comment c : issue.getComments()) {
            if(c.getVisibility() == null || !"Developers".equals(c.getVisibility().getValue())) {
                if(lastDate.isBefore(c.getCreationDate())) {
                    lastDate = c.getCreationDate();
                }
            }
        }
        Integer days = Double.valueOf(Math.floor((new DateTime().getMillis() - lastDate.getMillis())
                / HOURS_PER_DAY)).intValue();

        if(days > 3) {
            longWaitingActiveTickets.put(issue.getKey(), days);
        }

        issue.getLabels().stream().filter(label -> label.equals(ftsLabel)).forEach(label -> {
            checkFTSLabel(issue, days, FTS);
        });
        if(!FTS && issue.getPriority().getName().endsWith(" - P1")) {
            increaseMemberValue(issuesP1, issue.getAssignee().getName(), 1);
            increaseMemberValue(issuesP1DaysWithoutUpdate, issue.getAssignee().getName(), days);
        } else if(!FTS && issue.getPriority().getName().endsWith(" - P2")) {
            increaseMemberValue(issuesP2, issue.getAssignee().getName(), 1);
            increaseMemberValue(issuesP2DaysWithoutUpdate, issue.getAssignee().getName(), days);
        } else if(!FTS) {
            increaseMemberValue(issuesOther, issue.getAssignee().getName(), 1);
            increaseMemberValue(issuesOtherDaysWithoutUpdate, issue.getAssignee().getName(), days);
        }
        System.out.print(".");
    }

    public static void main(String[] args) throws Exception {
        File membersFile = null;
        for(int i = 0; i < args.length; i++) {
            switch(args[i]) {
                case "-f": {
                    if(i < args.length) {
                        membersFile = new File(args[i + 1]);
                        i++;
                    }
                    break;
                }
            }
        }

        if(membersFile == null) {
            System.out.println("ERROR: members file is not defined. Please use -f <members file path>");
        } else if(!membersFile.exists()) {
            System.out.println("ERROR: Members file [" + membersFile.getAbsolutePath() + "] doesn't exists");
        }

        readMembers(membersFile);

        JiraRestClientFactory f = new AsynchronousJiraRestClientFactory();
        JiraRestClient jc = f.createWithBasicHttpAuthentication(new URI("https://jira.mongodb.org"), USER, PASSWORD);

        StringBuilder sb = new StringBuilder();
        for(String member : teamMembers) {
            if(sb.length() > 0) {
                sb.append(",");
            } else {
                sb.append("assignee in (");
            }
            sb.append("\"");
            sb.append(member);
            sb.append("\"");
        }
        System.out.print("-> Contacting Jira:");
        sb.append(") AND project in (CS, MMSSUPPORT, SUPPORT) AND status not in (Closed, Resolved, \"Waiting for Customer\", \"Waiting for bug fix\", \"Waiting for Feature\")");
        SearchResult r = jc.getSearchClient().searchJql(sb.toString(), 4000, 0, null).claim();
        System.out.println(" done");

        System.out.print("-> Reading issues: ");
        try {
            /*
             Parallel execution
             */
            StreamSupport.stream(r.getIssues().spliterator(), true).forEach(basicIssue -> {
                try {
                    processIssue(jc, basicIssue);
                } catch(ExecutionException e) {
                    e.printStackTrace();
                } catch(InterruptedException e) {
                    e.printStackTrace();
                }
            });
        } finally {
            jc.close();
        }
        System.out.println(" done");

        printStats();
        printLongWaiting();
    }

    private static void printStats() {
        final Long multiplier = 1000L;
        Map<String, Long> teamMemberLevels = new HashMap<>();
        teamMembers.stream().forEach(member -> {
            if(issuesFTS.containsKey(member)) {
                teamMemberLevels.put(member, (3 * multiplier) + issuesFTSDaysWithoutUpdate.getOrDefault(member, 0));
            } else if(issuesP1.containsKey(member)) {
                teamMemberLevels.put(member, (2 * multiplier) + issuesP1DaysWithoutUpdate.getOrDefault(member, 0));
            } else if(issuesP2.containsKey(member)) {
                teamMemberLevels.put(member, (1 * multiplier) + issuesP2DaysWithoutUpdate.getOrDefault(member, 0));
            } else if(issuesOther.containsKey(member)) {
                teamMemberLevels.put(member, issuesOtherDaysWithoutUpdate.getOrDefault(member, 0).longValue());
            } else {
                teamMemberLevels.put(member, 0L);
            }
        });

        final Integer FIRST_COLUMN_LENGTH = 34;
        System.out.println();
        System.out.print("Member");
        System.out.format("%" + (FIRST_COLUMN_LENGTH - "Member".length()) + "s", "\t");
        System.out.print("    FTS");
        System.out.format("%7s", "\t");
        System.out.print("P1");
        System.out.format("%7s", "\t");
        System.out.print("P2");
        System.out.format("%7s", "\t");
        System.out.print("P3/P4");
        System.out.println();

        order = 1;
        entriesSortedByValues(teamMemberLevels).stream().forEach(member -> {
            String username = member.getKey();
            Integer padding = FIRST_COLUMN_LENGTH - username.length();
            if(padding < 0) {
                username = username.substring(0, FIRST_COLUMN_LENGTH);
            }
            System.out.print(order + ". " + username);
            System.out.format("%" + padding + "s", "\t");
            System.out.print(getMapValue(issuesFTS, username));
            System.out.format("(");
            System.out.print(getMapValue(issuesFTSDaysWithoutUpdate, username));
            System.out.format(")");
            System.out.format("%5s", "\t");
            System.out.print(getMapValue(issuesP1, username));
            System.out.format("(");
            System.out.print(getMapValue(issuesP1DaysWithoutUpdate, username));
            System.out.format(")");
            System.out.format("%5s", "\t");
            System.out.print(getMapValue(issuesP2, username));
            System.out.format("(");
            System.out.print(getMapValue(issuesP2DaysWithoutUpdate, username));
            System.out.format(")");
            System.out.format("%5s", "\t");
            System.out.print(getMapValue(issuesOther, username));
            System.out.format("(");
            System.out.print(getMapValue(issuesOtherDaysWithoutUpdate, username));
            System.out.format(")");
            System.out.println();
            order++;
        });
    }

    private static void printLongWaiting() {
        System.out.println();
        System.out.println("Long waiting active tickets:");
        entriesSortedByValues(longWaitingActiveTickets).forEach(ticket -> {
            System.out.print(ticket.getKey());
            System.out.print(" (");
            System.out.print(ticket.getValue());
            System.out.print(")");
            System.out.println();
        });
    }

    private static Integer getMapValue(Map<String, Integer> map, String member) {
        if(map.containsKey(member)) {
            return map.get(member);
        } else {
            return 0;
        }
    }

    private static <K,V extends Comparable<? super V>> List<Map.Entry<K, V>> entriesSortedByValues(Map<K,V> map) {
        List<Map.Entry<K,V>> sortedEntries = new ArrayList<Map.Entry<K,V>>(map.entrySet());
        Collections.sort(sortedEntries,
                new Comparator<Map.Entry<K,V>>() {
                    @Override
                    public int compare(Map.Entry<K,V> e1, Map.Entry<K,V> e2) {
                        return e1.getValue().compareTo(e2.getValue());
                    }
                }
        );
        return sortedEntries;
    }
}